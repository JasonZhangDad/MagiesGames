"""房间编排层:座位、AI 补位、回合计时、托管、断线重连、结算入库、快照广播。

并发模型:全部状态变更发生在事件循环的同步段内;每次成功动作 version+=1,
定时器/机器人任务醒来后核对 version,过期即放弃 —— 杜绝旧任务操作新状态。
"""
import asyncio
import random
import time

from . import config, db
from .game.ai import choose_action, choose_call
from .game.ai import hint as ai_hint
from .game.cards import rank_of
from .game.engine import DdzMatch
from .game.patterns import KIND_LABEL

BOT_NAMES = ["AI·星尘", "AI·闪电", "AI·大圣", "AI·夜枭", "AI·白泽", "AI·青鸾", "AI·墨影", "AI·雷酱"]
BOT_AVATARS = ["🤖", "👾", "🛸", "🎯"]


class Seat:
    def __init__(self, user: dict | None = None, bot_name: str | None = None):
        self.is_bot = user is None
        self.user_id = None if self.is_bot else user["id"]
        self.nickname = bot_name if self.is_bot else user["nickname"]
        self.avatar = random.choice(BOT_AVATARS) if self.is_bot else user["avatar"]
        self.coin = random.randint(6000, 66000) if self.is_bot else user["coin"]
        self.ready = self.is_bot
        self.connected = True  # 能加入就说明在线;掉线由 on_disconnect 标记
        self.auto = False
        self.last_chat = 0.0
        self.last_bubble: dict | None = None


class Room:
    def __init__(self, manager: "RoomManager", code: str, owner_id: int, private: bool):
        self.manager = manager
        self.code = code
        self.owner_id = owner_id
        self.private = private
        self.seats: list[Seat | None] = [None, None, None]
        self.match: DdzMatch | None = None
        self.version = 0
        self.turn_deadline: float | None = None
        self.started_at: float | None = None
        self.closed = False
        self._tasks: set[asyncio.Task] = set()

    # ---------- 小工具 ----------

    @property
    def phase(self) -> str:
        return self.match.phase if self.match else "waiting"

    def seat_of(self, uid: int) -> int | None:
        for i, s in enumerate(self.seats):
            if s and s.user_id == uid:
                return i
        return None

    def humans(self) -> list[Seat]:
        return [s for s in self.seats if s and not s.is_bot]

    def _spawn(self, coro):
        t = asyncio.get_running_loop().create_task(coro)
        self._tasks.add(t)
        t.add_done_callback(self._tasks.discard)

    def _close(self):
        self.closed = True
        for t in self._tasks:
            t.cancel()
        self.manager.drop_room(self.code)

    # ---------- 进出与准备 ----------

    def join(self, user: dict) -> int:
        if self.seat_of(user["id"]) is not None:
            raise ValueError("你已经在这个房间里了")
        if self.phase not in ("waiting", "settled"):
            raise ValueError("对局进行中,不能加入")
        for i in range(3):
            if self.seats[i] is None:
                self.seats[i] = Seat(user=user)
                self.event({"e": "join", "seat": i, "nickname": user["nickname"]})
                self.broadcast()
                return i
        raise ValueError("房间已满")

    def leave(self, uid: int):
        i = self.seat_of(uid)
        if i is None:
            return
        self.manager.user_room.pop(uid, None)
        s = self.seats[i]
        if self.match and self.match.phase in ("calling", "playing"):
            # 对局中离开:席位转为 AI 代打,保住牌局
            s.is_bot = True
            s.user_id = None
            s.nickname = f"AI·代打"
            s.avatar = "🤖"
            s.ready = s.connected = True
            s.auto = False
            self.event({"e": "leave", "seat": i})
            self.drive()
        else:
            self.seats[i] = None
            self.event({"e": "leave", "seat": i})
        if not self.humans():
            self._close()
            return
        self.broadcast()

    def set_ready(self, uid: int, ready: bool):
        if self.phase not in ("waiting", "settled"):
            raise ValueError("对局进行中")
        i = self.seat_of(uid)
        if i is None:
            raise ValueError("你不在房间里")
        self.seats[i].ready = ready
        self.event({"e": "ready", "seat": i, "ready": ready})
        if ready:
            self._spawn(self._fill_bots_later(self.version))
        self.maybe_start()
        if not self.closed:
            self.broadcast()

    async def _fill_bots_later(self, version: int):
        await asyncio.sleep(config.FILL_BOTS_AFTER)
        if self.closed or self.version != version or self.phase not in ("waiting", "settled"):
            return
        if not any(s and s.ready and not s.is_bot for s in self.seats):
            return
        names = [n for n in BOT_NAMES if all(not s or s.nickname != n for s in self.seats)]
        random.shuffle(names)
        filled = False
        for i in range(3):
            if self.seats[i] is None:
                self.seats[i] = Seat(bot_name=names.pop())
                self.event({"e": "bot_fill", "seat": i, "nickname": self.seats[i].nickname})
                filled = True
        if filled:
            self.broadcast()
        self.maybe_start()

    def maybe_start(self):
        if self.phase not in ("waiting", "settled"):
            return
        if all(s and s.ready for s in self.seats):
            self.start_match()

    def start_match(self):
        self.match = DdzMatch(first_seat=random.randrange(3))
        self.started_at = time.time()
        self.version += 1
        for s in self.seats:
            s.ready = False
            s.auto = False if not s.is_bot else s.auto
            s.last_bubble = None
        self.event({"e": "deal"})
        self._arm_turn()
        self.broadcast()
        self.drive()

    # ---------- 回合驱动 ----------

    def _arm_turn(self):
        if not self.match or self.match.phase not in ("calling", "playing"):
            self.turn_deadline = None
            return
        limit = config.CALL_TIMEOUT if self.match.phase == "calling" else config.PLAY_TIMEOUT
        self.turn_deadline = time.time() + limit
        self._spawn(self._turn_timer(self.version, limit))

    async def _turn_timer(self, version: int, delay: float):
        await asyncio.sleep(delay)
        if self.closed or self.version != version:
            return
        seat_no = self.match.current
        s = self.seats[seat_no]
        if not s.is_bot and not s.auto:
            s.auto = True  # 超时自动托管
            self.event({"e": "auto", "seat": seat_no, "on": True})
        self._act_ai(seat_no)

    def drive(self):
        """轮到机器人/托管/掉线玩家时,安排 AI 代打。"""
        if self.closed or not self.match or self.match.phase not in ("calling", "playing"):
            return
        seat_no = self.match.current
        s = self.seats[seat_no]
        if s.is_bot or s.auto or not s.connected:
            delay = random.uniform(*config.BOT_DELAY) if s.is_bot else config.AUTO_DELAY
            self._spawn(self._bot_move(self.version, delay))

    async def _bot_move(self, version: int, delay: float):
        await asyncio.sleep(delay)
        if self.closed or self.version != version:
            return
        self._act_ai(self.match.current)

    def _act_ai(self, seat_no: int):
        m = self.match
        try:
            if m.phase == "calling":
                zeros = sum(1 for c in m.calls if c == 0)
                must = m.redeal_count >= 1 and zeros == 2
                self.do_call(seat_no, choose_call(m.hands[seat_no], m.max_call(), must=must))
            elif m.phase == "playing":
                action, cards = choose_action(m, seat_no)
                if action == "play":
                    self.do_play(seat_no, cards)
                else:
                    self.do_pass(seat_no)
        except ValueError:
            pass  # 版本竞争兜底:引擎拒绝即放弃本次代打

    # ---------- 三种对局动作(人类与 AI 共用) ----------

    def do_call(self, seat_no: int, score: int):
        ev = self.match.call(seat_no, score)
        self.version += 1
        s = self.seats[seat_no]
        s.last_bubble = {"kind": "call", "score": score}
        self.event({"e": "call", "seat": seat_no, "score": score})
        if ev["event"] == "landlord":
            self.event({"e": "landlord", "seat": ev["seat"], "bottom": self.match.bottom,
                        "base": self.match.base})
        elif ev["event"] == "redeal":
            for st in self.seats:
                st.last_bubble = None
            self.event({"e": "redeal"})
        self._arm_turn()
        self.broadcast()
        self.drive()

    def do_play(self, seat_no: int, cards: list[int]):
        ev = self.match.play(seat_no, cards)
        self.version += 1
        s = self.seats[seat_no]
        p = ev["pattern"]
        s.last_bubble = {"kind": "play"}
        self.event({"e": "play", "seat": seat_no, "cards": sorted(cards, key=rank_of),
                    "kind": p.kind, "kind_label": KIND_LABEL[p.kind],
                    "cards_left": len(self.match.hands[seat_no])})
        if self.match.phase == "settled":
            self._on_settle()
        else:
            self._arm_turn()
        self.broadcast()
        self.drive()

    def do_pass(self, seat_no: int):
        self.match.pass_(seat_no)
        self.version += 1
        self.seats[seat_no].last_bubble = {"kind": "pass"}
        self.event({"e": "pass", "seat": seat_no})
        self._arm_turn()
        self.broadcast()
        self.drive()

    # ---------- 结算 ----------

    def _on_settle(self):
        m = self.match
        r = m.result
        self.turn_deadline = None
        players = []
        for i, s in enumerate(self.seats):
            delta = r["deltas"][i]
            players.append({
                "user_id": s.user_id, "nickname": s.nickname, "is_bot": s.is_bot,
                "seat_no": i, "role": m.role_of(i),
                "delta_coin": delta * config.COIN_UNIT, "delta_rank": delta,
            })
        db.record_match(self.code, self.started_at or time.time(), r, players, m.history)
        for i, s in enumerate(self.seats):
            if s.is_bot:
                s.coin = max(0, s.coin + r["deltas"][i] * config.COIN_UNIT)
                s.ready = True
            else:
                u = db.get_user(s.user_id)
                if u:
                    s.coin = u["coin"]
                s.ready = False
                s.auto = False
        self.event({"e": "settle", "result": {
            **{k: r[k] for k in ("winner_seat", "winner_role", "spring", "bombs",
                                 "base", "multiplier", "deltas")},
            "coin_deltas": [d * config.COIN_UNIT for d in r["deltas"]],
            "hands_left": r["hands_left"],
        }})
        # 掉线玩家在局后清出房间
        for i, s in enumerate(self.seats):
            if s and not s.is_bot and not s.connected:
                self.seats[i] = None
        if not self.humans():
            self._close()

    # ---------- 断线 / 重连 ----------

    def on_disconnect(self, uid: int):
        i = self.seat_of(uid)
        if i is None:
            return
        s = self.seats[i]
        s.connected = False
        if self.match and self.match.phase in ("calling", "playing"):
            self.event({"e": "offline", "seat": i})
            self.broadcast()
            self.drive()  # 掉线玩家的回合交给 AI
        else:
            self._spawn(self._remove_if_gone(uid))

    async def _remove_if_gone(self, uid: int, grace: float = 30.0):
        await asyncio.sleep(grace)
        if self.closed:
            return
        i = self.seat_of(uid)
        if i is not None and not self.seats[i].connected \
                and self.phase in ("waiting", "settled"):
            self.leave(uid)

    def on_reconnect(self, uid: int):
        i = self.seat_of(uid)
        if i is None:
            return
        s = self.seats[i]
        s.connected = True
        s.auto = False
        self.event({"e": "online", "seat": i})
        self.broadcast()

    def set_auto(self, uid: int, on: bool):
        i = self.seat_of(uid)
        if i is None:
            raise ValueError("你不在房间里")
        self.seats[i].auto = on
        self.event({"e": "auto", "seat": i, "on": on})
        self.broadcast()
        if on:
            self.drive()

    # ---------- 聊天 ----------

    def chat(self, uid: int, text: str):
        i = self.seat_of(uid)
        if i is None:
            raise ValueError("你不在房间里")
        s = self.seats[i]
        now = time.time()
        if now - s.last_chat < 0.8:
            raise ValueError("发言太快了")
        text = text.strip()[:60]
        if not text:
            raise ValueError("不能发送空消息")
        s.last_chat = now
        self.event({"e": "chat", "seat": i, "text": text})

    # ---------- 快照与广播 ----------

    def hint_for(self, uid: int) -> list[int] | None:
        i = self.seat_of(uid)
        if i is None or not self.match or self.match.phase != "playing" \
                or self.match.current != i:
            return None
        return ai_hint(self.match, i)

    def snapshot(self, uid: int | None) -> dict:
        m = self.match
        my_seat = self.seat_of(uid) if uid is not None else None
        seats = []
        for i, s in enumerate(self.seats):
            if s is None:
                seats.append(None)
                continue
            seats.append({
                "seat": i, "nickname": s.nickname, "avatar": s.avatar, "coin": s.coin,
                "bot": s.is_bot, "ready": s.ready, "connected": s.connected, "auto": s.auto,
                "cards_left": len(m.hands[i]) if m else 0,
                "call": m.calls[i] if m and m.phase == "calling" else None,
                "role": (m.role_of(i) if m and m.landlord is not None else None),
                "bubble": s.last_bubble,
            })
        st = {
            "code": self.code, "private": self.private, "phase": self.phase,
            "owner": self.owner_id, "seats": seats, "my_seat": my_seat,
            "current": m.current if m and m.phase in ("calling", "playing") else None,
            "deadline": self.turn_deadline,
            "base": m.base if m else 0,
            "bombs": m.bombs if m else 0,
            "max_call": m.max_call() if m and m.phase == "calling" else 0,
            "landlord": m.landlord if m else None,
            "bottom": (m.bottom if m and m.landlord is not None else None),
            "last": ({"seat": m.last_seat, "cards": m.last_cards,
                      "kind_label": KIND_LABEL[m.last_pattern.kind]}
                     if m and m.last_pattern else None),
            "leading": (m.is_leading() if m and m.phase == "playing" else False),
        }
        if m and my_seat is not None and m.phase in ("calling", "playing", "settled"):
            st["my_hand"] = sorted(m.hands[my_seat], key=rank_of)
        if m and m.phase == "settled" and m.result:
            r = m.result
            st["result"] = {**{k: r[k] for k in ("winner_seat", "winner_role", "spring",
                                                 "bombs", "base", "multiplier", "deltas")},
                            "coin_deltas": [d * config.COIN_UNIT for d in r["deltas"]],
                            "hands_left": r["hands_left"]}
        return st

    def event(self, e: dict):
        self.manager.push_event(self, e)

    def broadcast(self):
        self.manager.push_state(self)

    def summary(self) -> dict:
        return {
            "code": self.code, "phase": self.phase,
            "players": [{"nickname": s.nickname, "avatar": s.avatar, "bot": s.is_bot}
                        for s in self.seats if s],
            "seats_free": sum(1 for s in self.seats if s is None),
        }


class RoomManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self.user_room: dict[int, str] = {}
        self.send_fn = None  # ws 层注入: send_fn(uid, msg_dict)

    # ---------- 房间生命周期 ----------

    def _gen_code(self) -> str:
        while True:
            code = f"{random.randint(0, 999999):06d}"
            if code not in self.rooms:
                return code

    def room_of(self, uid: int) -> Room | None:
        code = self.user_room.get(uid)
        return self.rooms.get(code) if code else None

    def create(self, user: dict, private: bool = False) -> Room:
        self._leave_current(user["id"])
        room = Room(self, self._gen_code(), user["id"], private)
        self.rooms[room.code] = room
        room.join(user)
        self.user_room[user["id"]] = room.code
        return room

    def join_code(self, user: dict, code: str) -> Room:
        room = self.rooms.get(code)
        if not room:
            raise ValueError("房间不存在或已解散")
        self._leave_current(user["id"])
        room.join(user)
        self.user_room[user["id"]] = room.code
        return room

    def quick_match(self, user: dict) -> Room:
        self._leave_current(user["id"])
        for room in self.rooms.values():
            if not room.private and room.phase in ("waiting",) \
                    and any(s is None for s in room.seats):
                room.join(user)
                self.user_room[user["id"]] = room.code
                return room
        return self.create(user, private=False)

    def _leave_current(self, uid: int):
        room = self.room_of(uid)
        if room:
            room.leave(uid)
        self.user_room.pop(uid, None)

    def leave(self, uid: int):
        self._leave_current(uid)

    def drop_room(self, code: str):
        room = self.rooms.pop(code, None)
        if room:
            for uid, c in list(self.user_room.items()):
                if c == code:
                    self.user_room.pop(uid, None)

    def list_public(self) -> list[dict]:
        return [r.summary() for r in self.rooms.values() if not r.private]

    # ---------- 推送 ----------

    def push_event(self, room: Room, e: dict):
        if not self.send_fn:
            return
        for s in room.seats:
            if s and not s.is_bot and s.connected:
                self.send_fn(s.user_id, {"t": "EVENT", "e": e})

    def push_state(self, room: Room):
        if not self.send_fn:
            return
        for s in room.seats:
            if s and not s.is_bot and s.connected:
                self.send_fn(s.user_id, {"t": "STATE", "state": room.snapshot(s.user_id)})


manager = RoomManager()
