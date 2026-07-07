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
from .game.gomoku import ai as gmk_ai
from .game.gomoku.engine import GomokuMatch
from .game.mahjong import ai as mj_ai
from .game.mahjong.engine import MahjongMatch
from .game.mahjong.tiles import kind_label, kind_of
from .game.patterns import KIND_LABEL
from .game.xiangqi import ai as xq_ai
from .game.xiangqi.engine import XiangqiMatch
from .game.xiangqi.engine import label_of as xq_label

SEATS_OF = {"ddz": 3, "mahjong": 4, "gomoku": 2, "xiangqi": 2}

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
    def __init__(self, manager: "RoomManager", code: str, owner_id: int, private: bool,
                 game: str = "ddz"):
        self.manager = manager
        self.code = code
        self.owner_id = owner_id
        self.private = private
        self.game = game
        self.nseats = SEATS_OF[game]
        self.seats: list[Seat | None] = [None] * self.nseats
        self.spectators: dict[int, dict] = {}  # uid → {nickname, avatar}
        self.match: DdzMatch | MahjongMatch | None = None
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
        for i in range(self.nseats):
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
        if self.match and self.match.phase != "settled":
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
        # 断线且未准备的玩家不该卡住整桌:清位后由 AI 补上
        for i, s in enumerate(self.seats):
            if s and not s.is_bot and not s.connected and not s.ready:
                self.manager.user_room.pop(s.user_id, None)
                self.seats[i] = None
                self.event({"e": "leave", "seat": i})
        names = [n for n in BOT_NAMES if all(not s or s.nickname != n for s in self.seats)]
        random.shuffle(names)
        filled = False
        for i in range(self.nseats):
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
        if self.game == "ddz":
            self.match = DdzMatch(first_seat=random.randrange(3))
        elif self.game == "gomoku":
            self.match = GomokuMatch(first=random.randrange(2))
        elif self.game == "xiangqi":
            self.match = XiangqiMatch(red_seat=random.randrange(2))
        else:
            self.match = MahjongMatch(dealer=random.randrange(4), exchange=True)
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
        m = self.match
        if not m or m.phase in ("settled",) or self.phase == "waiting":
            self.turn_deadline = None
            return
        if self.game == "ddz" and m.phase == "calling":
            limit = config.CALL_TIMEOUT
        elif self.game == "mahjong" and m.phase in ("exchange", "dingque"):
            limit = config.LACK_TIMEOUT
        elif self.game == "mahjong" and m.claiming:
            limit = config.CLAIM_TIMEOUT
        else:
            limit = config.PLAY_TIMEOUT
        self.turn_deadline = time.time() + limit
        self._spawn(self._turn_timer(self.version, limit))

    async def _turn_timer(self, version: int, delay: float):
        await asyncio.sleep(delay)
        if self.closed or self.version != version:
            return
        m = self.match
        if self.game == "mahjong":
            if m.phase == "exchange":
                for i, s in enumerate(self.seats):
                    if m.exchange_sel[i] is None:
                        self._mark_auto(i)
                        self._act_ai(i)
                return
            if m.phase == "dingque":
                for i, s in enumerate(self.seats):
                    if m.lacks[i] is None:
                        self._mark_auto(i)
                        self._act_ai(i)
                return
            if m.claiming:
                for i in list(m.claiming["options"]):
                    if i not in m.claiming["responses"]:
                        self._mark_auto(i)
                        self._act_ai(i)
                return
        seat_no = m.current
        if seat_no is None:
            return
        self._mark_auto(seat_no)
        self._act_ai(seat_no)

    def _mark_auto(self, seat_no: int):
        s = self.seats[seat_no]
        if not s.is_bot and not s.auto:
            s.auto = True  # 超时自动托管
            self.event({"e": "auto", "seat": seat_no, "on": True})

    def drive(self):
        """轮到机器人/托管/掉线玩家时,安排 AI 代打。"""
        if self.closed or not self.match or self.match.phase == "settled" \
                or self.phase == "waiting":
            return
        m = self.match

        def needs_ai(s: Seat) -> bool:
            return s.is_bot or s.auto or not s.connected

        pending: list[int] = []
        if self.game == "mahjong":
            if m.phase == "exchange":
                pending = [i for i, s in enumerate(self.seats)
                           if m.exchange_sel[i] is None and needs_ai(s)]
            elif m.phase == "dingque":
                pending = [i for i, s in enumerate(self.seats)
                           if m.lacks[i] is None and needs_ai(s)]
            elif m.claiming:
                pending = [i for i in m.claiming["options"]
                           if i not in m.claiming["responses"] and needs_ai(self.seats[i])]
            elif m.current is not None and needs_ai(self.seats[m.current]):
                pending = [m.current]
        else:
            if m.phase in ("calling", "playing") and needs_ai(self.seats[m.current]):
                pending = [m.current]
        for seat_no in pending:
            s = self.seats[seat_no]
            delay = random.uniform(*config.BOT_DELAY) if s.is_bot else config.AUTO_DELAY
            self._spawn(self._bot_move(self.version, delay, seat_no))

    async def _bot_move(self, version: int, delay: float, seat_no: int):
        await asyncio.sleep(delay)
        if self.closed or self.version != version:
            return
        self._act_ai(seat_no)

    def _act_ai(self, seat_no: int):
        m = self.match
        try:
            if self.game == "mahjong":
                self._act_ai_mj(seat_no)
            elif self.game == "gomoku":
                if m.phase == "playing" and m.current == seat_no:
                    x, y = gmk_ai.choose_move(m, seat_no)
                    self.do_place(seat_no, x, y)
            elif self.game == "xiangqi":
                if m.phase == "playing" and m.current == seat_no:
                    mv = xq_ai.choose_move(m, seat_no)
                    if mv:
                        self.do_xqmove(seat_no, mv[0], mv[1])
            elif m.phase == "calling":
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

    def _act_ai_mj(self, seat_no: int):
        m = self.match
        if m.phase == "exchange":
            if m.exchange_sel[seat_no] is None:
                self.do_exchange(seat_no, mj_ai.choose_exchange(m.hands[seat_no]))
            return
        if m.phase == "dingque":
            if m.lacks[seat_no] is None:
                self.do_lack(seat_no, mj_ai.choose_lack(m.hands[seat_no]))
            return
        if m.claiming:
            if seat_no in m.claiming["options"] and seat_no not in m.claiming["responses"]:
                self.do_claim(seat_no, mj_ai.choose_claim(m, seat_no))
            return
        if m.current != seat_no:
            return
        action, arg = mj_ai.choose_self_action(m, seat_no)
        if action == "hu":
            self.do_hu(seat_no)
        elif action == "angang":
            self.do_angang(seat_no, arg)
        elif action == "bugang":
            self.do_bugang(seat_no, arg)
        else:
            self.do_discard(seat_no, arg)

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

    # ---------- 五子棋动作(人类与 AI 共用) ----------

    def do_place(self, seat_no: int, x: int, y: int):
        m = self.match
        m.place(seat_no, x, y)
        self.version += 1
        self.event({"e": "place", "seat": seat_no, "x": x, "y": y})
        if m.phase == "settled":
            self._on_settle_gmk()
        else:
            self._arm_turn()
        self.broadcast()
        self.drive()

    def _gmk_result(self) -> dict:
        r = self.match.result
        return {**r, "coin_deltas": [d * config.COIN_UNIT for d in r["deltas"]]}

    def _on_settle_gmk(self):
        m = self.match
        r = m.result
        self.turn_deadline = None
        players = []
        for i, s in enumerate(self.seats):
            role = "draw" if r["winner_seat"] is None else \
                ("winner" if r["winner_seat"] == i else "loser")
            players.append({
                "user_id": s.user_id, "nickname": s.nickname, "is_bot": s.is_bot,
                "seat_no": i, "role": role,
                "delta_coin": r["deltas"][i] * config.COIN_UNIT, "delta_rank": r["deltas"][i],
            })
        db.record_match(self.code, self.started_at or time.time(), {
            "base": 1, "multiplier": 1,
            "winner_role": "draw" if r["winner_seat"] is None else "winner",
            "spring": False, "bombs": 0,
        }, players, m.history, game_type="gomoku")
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
        self.event({"e": "gmk_settle", "result": self._gmk_result()})
        for i, s in enumerate(self.seats):
            if s and not s.is_bot and not s.connected:
                self.seats[i] = None
        if not self.humans():
            self._close()

    # ---------- 象棋动作(人类与 AI 共用) ----------

    def do_xqmove(self, seat_no: int, frm, to):
        m = self.match
        frm = (int(frm[0]), int(frm[1]))
        to = (int(to[0]), int(to[1]))
        m.move(seat_no, frm, to)
        self.version += 1
        rec = m.last
        side = m.side_of(seat_no)
        ev = {"e": "xqmove", "seat": seat_no, "from": rec["from"], "to": rec["to"],
              "kind": rec["kind"], "label": xq_label(side, rec["kind"]),
              "captured": rec["captured"],
              "check": m.phase == "playing" and m.in_check(1 - side)}
        self.event(ev)
        if m.phase == "settled":
            self._on_settle_xq()
        else:
            self._arm_turn()
        self.broadcast()
        self.drive()

    def _xq_result(self) -> dict:
        r = self.match.result
        return {**r, "coin_deltas": [d * config.COIN_UNIT for d in r["deltas"]]}

    def _on_settle_xq(self):
        m = self.match
        r = m.result
        self.turn_deadline = None
        players = []
        for i, s in enumerate(self.seats):
            role = "draw" if r["winner_seat"] is None else \
                ("winner" if r["winner_seat"] == i else "loser")
            players.append({
                "user_id": s.user_id, "nickname": s.nickname, "is_bot": s.is_bot,
                "seat_no": i, "role": role,
                "delta_coin": r["deltas"][i] * config.COIN_UNIT, "delta_rank": r["deltas"][i],
            })
        db.record_match(self.code, self.started_at or time.time(), {
            "base": 1, "multiplier": 1,
            "winner_role": "draw" if r["winner_seat"] is None else "winner",
            "spring": False, "bombs": 0,
        }, players, m.history, game_type="xiangqi")
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
        self.event({"e": "xq_settle", "result": self._xq_result()})
        for i, s in enumerate(self.seats):
            if s and not s.is_bot and not s.connected:
                self.seats[i] = None
        if not self.humans():
            self._close()

    # ---------- 麻将动作(人类与 AI 共用) ----------

    def _mj_after(self, ev: dict | None = None):
        self.version += 1
        if ev:
            self.event(ev)
        if self.match.phase == "settled":
            self._on_settle_mj()
        else:
            self._arm_turn()
        self.broadcast()
        self.drive()

    def do_exchange(self, seat_no: int, tiles: list[int]):
        m = self.match
        m.set_exchange(seat_no, tiles)
        if m.phase == "dingque":  # 全员已换,公布方向
            self.event({"e": "exchanged", "seat": seat_no})
            self._mj_after({"e": "exchange_done", "dir": m.exchange_dir})
        else:
            self._mj_after({"e": "exchanged", "seat": seat_no})

    def do_lack(self, seat_no: int, suit: int):
        self.match.set_lack(seat_no, suit)
        self._mj_after({"e": "lack", "seat": seat_no, "suit": suit})

    def do_discard(self, seat_no: int, tile: int):
        m = self.match
        m.discard(seat_no, tile)
        ev = {"e": "discard", "seat": seat_no, "tile": tile,
              "label": kind_label(kind_of(tile))}
        if m.claiming:
            ev["claim_seats"] = list(m.claiming["options"])
        self._mj_after(ev)

    def do_claim(self, seat_no: int, action: str):
        m = self.match
        before_out = set(m.out)
        hlen = len(m.history)
        m.claim(seat_no, action)
        ev = None
        if m.claiming is None:  # 全员已响应,已裁决
            new_winners = [w for w in m.winners if w["seat"] not in before_out]
            if new_winners:
                ev = {"e": "hu_multi",
                      "winners": [{k: w[k] for k in ("seat", "fan", "names", "zimo", "from_seat")}
                                  for w in new_winners]}
            else:
                acts = [h for h in m.history[hlen:] if h.get("a") in ("peng", "gang")]
                if acts:
                    h = acts[0]
                    ev = {"e": h["a"], "seat": h["seat"], "kind": h["kind"],
                          "label": kind_label(h["kind"])}
                    if h["a"] == "gang":
                        ev["pay"] = m.last_gang_pay
        self._mj_after(ev)

    def do_angang(self, seat_no: int, kind: int):
        self.match.angang(seat_no, kind)
        self._mj_after({"e": "angang", "seat": seat_no, "kind": kind,
                        "label": kind_label(kind), "pay": self.match.last_gang_pay})

    def do_bugang(self, seat_no: int, kind: int):
        self.match.bugang(seat_no, kind)
        self._mj_after({"e": "bugang", "seat": seat_no, "kind": kind,
                        "label": kind_label(kind), "pay": self.match.last_gang_pay})

    def do_hu(self, seat_no: int):
        m = self.match
        m.hu_self(seat_no)
        w = m.winners[-1]
        self._mj_after({"e": "hu_multi",
                        "winners": [{k: w[k] for k in ("seat", "fan", "names", "zimo", "from_seat")}]})

    def _on_settle_mj(self):
        m = self.match
        r = m.result
        self.turn_deadline = None
        players = []
        for i, s in enumerate(self.seats):
            players.append({
                "user_id": s.user_id, "nickname": s.nickname, "is_bot": s.is_bot,
                "seat_no": i, "role": "winner" if any(w["seat"] == i for w in m.winners) else "player",
                "delta_coin": m.deltas[i] * config.COIN_UNIT, "delta_rank": m.deltas[i],
            })
        db.record_match(self.code, self.started_at or time.time(), {
            "base": 1, "multiplier": max((w["fan"] for w in m.winners), default=1),
            "winner_role": "draw" if r["draw"] else "hu",
            "spring": False, "bombs": 0,
        }, players, m.history, game_type="mahjong")
        for i, s in enumerate(self.seats):
            if s.is_bot:
                s.coin = max(0, s.coin + m.deltas[i] * config.COIN_UNIT)
                s.ready = True
            else:
                u = db.get_user(s.user_id)
                if u:
                    s.coin = u["coin"]
                s.ready = False
                s.auto = False
        self.event({"e": "mj_settle", "result": self._mj_result()})
        for i, s in enumerate(self.seats):
            if s and not s.is_bot and not s.connected:
                self.seats[i] = None
        if not self.humans():
            self._close()

    def _mj_result(self) -> dict:
        m = self.match
        r = m.result
        return {
            "draw": r["draw"],
            "winners": [{k: w[k] for k in ("seat", "fan", "names", "zimo", "from_seat", "hand")}
                        for w in m.winners],
            "deltas": r["deltas"],
            "coin_deltas": [d * config.COIN_UNIT for d in r["deltas"]],
            "hands_left": r["hands_left"],
            "lacks": r["lacks"],
        }

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
        if self.match and self.match.phase != "settled":
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
        if self.game == "mahjong":
            _, arg = mj_ai.choose_self_action(self.match, i)
            return [arg] if isinstance(arg, int) else None
        if self.game == "gomoku":
            return list(gmk_ai.choose_move(self.match, i))
        if self.game == "xiangqi":
            mv = xq_ai.choose_move(self.match, i)
            return [*mv[0], *mv[1]] if mv else None
        return ai_hint(self.match, i)

    def snapshot(self, uid: int | None) -> dict:
        m = self.match
        my_seat = self.seat_of(uid) if uid is not None else None
        seats = []
        for i, s in enumerate(self.seats):
            if s is None:
                seats.append(None)
                continue
            entry = {
                "seat": i, "nickname": s.nickname, "avatar": s.avatar, "coin": s.coin,
                "bot": s.is_bot, "ready": s.ready, "connected": s.connected, "auto": s.auto,
                "cards_left": len(m.hands[i]) if m and hasattr(m, "hands") else 0,
                "bubble": s.last_bubble,
            }
            if self.game == "ddz":
                entry["call"] = m.calls[i] if m and m.phase == "calling" else None
                entry["role"] = m.role_of(i) if m and m.landlord is not None else None
            elif self.game == "gomoku":
                entry["stone"] = ("black" if m.first == i else "white") if m else None
            elif self.game == "xiangqi":
                entry["camp"] = ("red" if m.red_seat == i else "black") if m else None
            else:
                entry["lack"] = m.lacks[i] if m else None
                entry["melds"] = ([{"type": x["type"], "kind": x["kind_id"],
                                    "label": kind_label(x["kind_id"])}
                                   for x in m.melds[i]] if m else [])
                entry["discards"] = m.discards[i] if m else []
                entry["hu"] = bool(m and i in m.out)
                entry["exchanged"] = bool(m and m.exchange_sel[i] is not None)
            seats.append(entry)
        st = {
            "code": self.code, "private": self.private, "phase": self.phase,
            "game": self.game, "owner": self.owner_id, "seats": seats,
            "my_seat": my_seat, "deadline": self.turn_deadline,
            "spectator": my_seat is None and uid in self.spectators,
            "watchers": len(self.spectators),
        }
        if self.game == "ddz":
            st.update({
                "current": m.current if m and m.phase in ("calling", "playing") else None,
                "base": m.base if m else 0,
                "bombs": m.bombs if m else 0,
                "max_call": m.max_call() if m and m.phase == "calling" else 0,
                "landlord": m.landlord if m else None,
                "bottom": (m.bottom if m and m.landlord is not None else None),
                "last": ({"seat": m.last_seat, "cards": m.last_cards,
                          "kind_label": KIND_LABEL[m.last_pattern.kind]}
                         if m and m.last_pattern else None),
                "leading": (m.is_leading() if m and m.phase == "playing" else False),
            })
            if m and my_seat is not None and m.phase in ("calling", "playing", "settled"):
                st["my_hand"] = sorted(m.hands[my_seat], key=rank_of)
            if m and m.phase == "settled" and m.result:
                r = m.result
                st["result"] = {**{k: r[k] for k in ("winner_seat", "winner_role", "spring",
                                                     "bombs", "base", "multiplier", "deltas")},
                                "coin_deltas": [d * config.COIN_UNIT for d in r["deltas"]],
                                "hands_left": r["hands_left"]}
        elif self.game == "gomoku":
            st.update({
                "current": m.current if m and m.phase == "playing" else None,
                "board": m.board if m else None,
                "last_move": ({"x": m.last[0], "y": m.last[1]} if m and m.last else None),
                "first": m.first if m else None,
            })
            if m and m.phase == "settled" and m.result:
                st["result"] = self._gmk_result()
        elif self.game == "xiangqi":
            side = m.side_of(my_seat) if m and my_seat is not None else None
            st.update({
                "current": m.current if m and m.phase == "playing" else None,
                "board": ([[f"{c[0]}{c[1]}" if c else None for c in row]
                           for row in m.board] if m else None),
                "red_seat": m.red_seat if m else None,
                "last_move": ({"from": m.last["from"], "to": m.last["to"]} if m and m.last else None),
                "in_check": bool(m and m.phase == "playing" and side is not None
                                 and m.turn_side == side and m.in_check(side)),
            })
            if m and m.phase == "playing" and my_seat is not None and m.current == my_seat:
                st["my_moves"] = [[f[0], f[1], t[0], t[1]]
                                  for f, t in m.legal_moves(m.side_of(my_seat))]
            if m and m.phase == "settled" and m.result:
                st["result"] = self._xq_result()
        else:
            st.update({
                "current": m.current if m and m.phase == "playing" else None,
                "wall_left": len(m.wall) if m else 0,
                "deltas": list(m.deltas) if m else [0, 0, 0, 0],
                "claiming": None,
            })
            if m and m.claiming:
                st["claiming"] = {"from": m.claiming["from"], "tile": m.claiming["tile"],
                                  "label": kind_label(kind_of(m.claiming["tile"])),
                                  "waiting": [i for i in m.claiming["options"]
                                              if i not in m.claiming["responses"]]}
                if my_seat in m.claiming["options"] and my_seat not in m.claiming["responses"]:
                    st["my_claim"] = m.claiming["options"][my_seat]
            if m and my_seat is not None and m.phase in ("exchange", "dingque", "playing", "settled"):
                st["my_hand"] = sorted(m.hands[my_seat])
                st["my_drawn"] = m.drawn if m.current == my_seat else None
                st["my_options"] = m.self_options(my_seat) if m.phase == "playing" else {}
            if m and m.phase == "settled" and m.result:
                st["result"] = self._mj_result()
        return st

    def event(self, e: dict):
        self.manager.push_event(self, e)

    def broadcast(self):
        self.manager.push_state(self)

    def summary(self) -> dict:
        return {
            "code": self.code, "phase": self.phase, "game": self.game,
            "players": [{"nickname": s.nickname, "avatar": s.avatar, "bot": s.is_bot}
                        for s in self.seats if s],
            "seats_free": sum(1 for s in self.seats if s is None),
        }


class RoomManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self.user_room: dict[int, str] = {}
        self.user_watch: dict[int, str] = {}  # 观战者 uid → 房号
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

    def create(self, user: dict, private: bool = False, game: str = "ddz") -> Room:
        if game not in SEATS_OF:
            raise ValueError("未知的游戏类型")
        self._leave_current(user["id"])
        room = Room(self, self._gen_code(), user["id"], private, game=game)
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

    def quick_match(self, user: dict, game: str = "ddz") -> Room:
        self._leave_current(user["id"])
        for room in self.rooms.values():
            if not room.private and room.game == game and room.phase == "waiting" \
                    and any(s is None for s in room.seats):
                room.join(user)
                self.user_room[user["id"]] = room.code
                return room
        return self.create(user, private=False, game=game)

    def watch(self, user: dict, code: str) -> Room:
        room = self.rooms.get(code)
        if not room:
            raise ValueError("房间不存在或已解散")
        self._leave_current(user["id"])
        room.spectators[user["id"]] = {"nickname": user["nickname"], "avatar": user["avatar"]}
        self.user_watch[user["id"]] = code
        if self.send_fn:
            self.send_fn(user["id"], {"t": "STATE", "state": room.snapshot(user["id"])})
        return room

    def unwatch(self, uid: int):
        code = self.user_watch.pop(uid, None)
        room = self.rooms.get(code) if code else None
        if room:
            room.spectators.pop(uid, None)

    def _leave_current(self, uid: int):
        room = self.room_of(uid)
        if room:
            room.leave(uid)
        self.user_room.pop(uid, None)
        self.unwatch(uid)

    def leave(self, uid: int):
        self._leave_current(uid)

    def drop_room(self, code: str):
        room = self.rooms.pop(code, None)
        if room:
            for uid, c in list(self.user_room.items()):
                if c == code:
                    self.user_room.pop(uid, None)
            for uid, c in list(self.user_watch.items()):
                if c == code:
                    self.user_watch.pop(uid, None)
                    if self.send_fn:
                        self.send_fn(uid, {"t": "STATE", "state": None})

    def list_public(self) -> list[dict]:
        return [r.summary() for r in self.rooms.values() if not r.private]

    # ---------- 推送 ----------

    def push_event(self, room: Room, e: dict):
        if not self.send_fn:
            return
        for s in room.seats:
            if s and not s.is_bot and s.connected:
                self.send_fn(s.user_id, {"t": "EVENT", "e": e})
        for uid in room.spectators:
            self.send_fn(uid, {"t": "EVENT", "e": e})

    def push_state(self, room: Room):
        if not self.send_fn:
            return
        for s in room.seats:
            if s and not s.is_bot and s.connected:
                self.send_fn(s.user_id, {"t": "STATE", "state": room.snapshot(s.user_id)})
        for uid in room.spectators:
            self.send_fn(uid, {"t": "STATE", "state": room.snapshot(uid)})


manager = RoomManager()
