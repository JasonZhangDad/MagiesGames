"""四川麻将(血战到底)状态机 —— 服务端唯一可信源,纯逻辑无 IO。

流程:dingque(定缺) → playing(摸打/碰杠/胡,胡牌离场继续打) → settled。
终局:三家胡牌 或 牌墙摸完。简化约定:无吃、无换三张、无抢杠胡、流局不查叫。
计分:番 n → 单位 2^(n-1);点炮者付,自摸时所有未胡玩家各付。
"""
import random
from collections import Counter

from .tiles import kind_of, kind_label, new_wall, suit_of
from .win import can_win, fan_of


class MahjongMatch:
    SEATS = 4

    def __init__(self, wall: list[int] | None = None, hands: list[list[int]] | None = None,
                 dealer: int = 0, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.dealer = dealer
        if hands is None:
            full = wall if wall is not None else new_wall(self.rng)
            self.hands = [sorted(full[i * 13:(i + 1) * 13]) for i in range(4)]
            self.wall = list(full[52:])
            self.wall.reverse()  # pop() 从尾部摸
        else:
            self.hands = [sorted(h) for h in hands]
            self.wall = list(wall or [])
        self.melds: list[list[dict]] = [[], [], [], []]
        self.discards: list[list[int]] = [[], [], [], []]
        self.lacks: list[int | None] = [None] * 4
        self.phase = "dingque"
        self.current: int | None = None
        self.drawn: int | None = None
        self.last_gang_draw = False
        self.claiming: dict | None = None  # {"tile","from","options":{seat:[..]},"responses":{}}
        self.out: set[int] = set()
        self.winners: list[dict] = []
        self.deltas = [0, 0, 0, 0]
        self.result: dict | None = None
        self.history: list[dict] = []

    # ---------- 工具 ----------

    def _require(self, cond: bool, msg: str):
        if not cond:
            raise ValueError(msg)

    def _cnt(self, seat: int, extra_kind: int | None = None) -> Counter:
        c = Counter(kind_of(t) for t in self.hands[seat])
        if extra_kind is not None:
            c[extra_kind] += 1
        return c

    def _lack_ok(self, seat: int, extra_kind: int | None = None) -> bool:
        lack = self.lacks[seat]
        if lack is None:
            return False
        kinds = [kind_of(t) for t in self.hands[seat]] + [m["kind_id"] for m in self.melds[seat]]
        if extra_kind is not None:
            kinds.append(extra_kind)
        return all(suit_of(k) != lack for k in kinds)

    def _can_hu(self, seat: int, extra_kind: int | None = None) -> bool:
        return self._lack_ok(seat, extra_kind) and can_win(self._cnt(seat, extra_kind))

    def active(self) -> list[int]:
        return [s for s in range(4) if s not in self.out]

    def _next_active(self, seat: int) -> int:
        s = (seat + 1) % 4
        while s in self.out:
            s = (s + 1) % 4
        return s

    # ---------- 定缺 ----------

    def set_lack(self, seat: int, suit: int):
        self._require(self.phase == "dingque", "现在不是定缺阶段")
        self._require(suit in (0, 1, 2), "缺门只能是 万/筒/条")
        self._require(self.lacks[seat] is None, "你已经定过缺了")
        self.lacks[seat] = suit
        self.history.append({"a": "lack", "seat": seat, "suit": suit})
        if all(v is not None for v in self.lacks):
            self.phase = "playing"
            self._draw(self.dealer)

    # ---------- 摸打 ----------

    def _draw(self, seat: int, gang: bool = False):
        if not self.wall:
            self._finish(draw=True)
            return
        tile = self.wall.pop()
        self.hands[seat].append(tile)
        self.hands[seat].sort()
        self.current = seat
        self.drawn = tile
        self.last_gang_draw = gang
        self.history.append({"a": "draw", "seat": seat})

    def self_options(self, seat: int) -> dict:
        """当前玩家可用的特殊操作:hu / angang(kinds) / bugang(kinds)。"""
        if self.phase != "playing" or self.claiming or seat != self.current:
            return {}
        opts: dict = {}
        if self.drawn is not None:
            if self._can_hu(seat):
                opts["hu"] = True
            cnt = self._cnt(seat)
            an = [k for k, c in cnt.items() if c == 4]
            if an:
                opts["angang"] = sorted(an)
            my_pengs = {m["kind_id"] for m in self.melds[seat] if m["type"] == "peng"}
            bu = [k for k in cnt if k in my_pengs]
            if bu:
                opts["bugang"] = sorted(bu)
        return opts

    def discard(self, seat: int, tile: int):
        self._require(self.phase == "playing" and not self.claiming, "现在不能出牌")
        self._require(seat == self.current, "还没轮到你")
        self._require(tile in self.hands[seat], "这张牌不在你手里")
        self.hands[seat].remove(tile)
        self.discards[seat].append(tile)
        self.drawn = None
        self.history.append({"a": "discard", "seat": seat, "tile": tile,
                             "label": kind_label(kind_of(tile))})
        kind = kind_of(tile)
        options: dict[int, list[str]] = {}
        for s in self.active():
            if s == seat:
                continue
            o = []
            if self._can_hu(s, kind):
                o.append("hu")
            cnt = self._cnt(s)
            if suit_of(kind) != self.lacks[s]:
                if cnt[kind] == 3:
                    o.append("gang")
                if cnt[kind] >= 2:
                    o.append("peng")
            if o:
                options[s] = o
        if options:
            self.claiming = {"tile": tile, "from": seat, "options": options, "responses": {}}
        else:
            self._draw(self._next_active(seat))

    # ---------- 碰杠胡响应 ----------

    def claim(self, seat: int, action: str):
        self._require(self.claiming is not None, "现在没有可响应的牌")
        opts = self.claiming["options"].get(seat)
        self._require(opts is not None, "你不能响应这张牌")
        self._require(seat not in self.claiming["responses"], "你已经选过了")
        self._require(action == "pass" or action in opts, "无效操作")
        self.claiming["responses"][seat] = action
        if len(self.claiming["responses"]) == len(self.claiming["options"]):
            self._resolve_claims()

    def _resolve_claims(self):
        cl = self.claiming
        self.claiming = None
        tile = cl["tile"]
        kind = kind_of(tile)
        src = cl["from"]
        resp = cl["responses"]
        hu_seats = [s for s in self._order_from(src) if resp.get(s) == "hu"]
        if hu_seats:
            self.discards[src].pop()  # 牌被胡走
            for s in hu_seats:
                self._settle_hu(s, zimo=False, from_seat=src, extra_tile=tile)
            if len(self.out) >= 3:
                self._finish(draw=False)
            else:
                self._draw(self._next_active(src))
            return
        for s in self._order_from(src):
            act = resp.get(s)
            if act in ("peng", "gang"):
                take = 3 if act == "gang" else 2
                removed = [t for t in self.hands[s] if kind_of(t) == kind][:take]
                for t in removed:
                    self.hands[s].remove(t)
                self.discards[src].pop()
                self.melds[s].append({"type": "gang" if act == "gang" else "peng",
                                      "kind_id": kind, "tiles": removed + [tile],
                                      "from_seat": src})
                self.history.append({"a": act, "seat": s, "kind": kind})
                if act == "gang":
                    self._draw(s, gang=True)
                else:
                    self.current = s
                    self.drawn = None
                return
        self._draw(self._next_active(src))

    def _order_from(self, seat: int):
        return [(seat + i) % 4 for i in range(1, 4)]

    # ---------- 杠(自回合) ----------

    def angang(self, seat: int, kind: int):
        opts = self.self_options(seat)
        self._require(kind in opts.get("angang", []), "不能暗杠这张牌")
        removed = [t for t in self.hands[seat] if kind_of(t) == kind]
        for t in removed:
            self.hands[seat].remove(t)
        self.melds[seat].append({"type": "angang", "kind_id": kind, "tiles": removed})
        self.history.append({"a": "angang", "seat": seat, "kind": kind})
        self._draw(seat, gang=True)

    def bugang(self, seat: int, kind: int):
        opts = self.self_options(seat)
        self._require(kind in opts.get("bugang", []), "不能补杠这张牌")
        tile = next(t for t in self.hands[seat] if kind_of(t) == kind)
        self.hands[seat].remove(tile)
        for m in self.melds[seat]:
            if m["type"] == "peng" and m["kind_id"] == kind:
                m["type"] = "bugang"
                m["tiles"].append(tile)
                break
        self.history.append({"a": "bugang", "seat": seat, "kind": kind})
        self._draw(seat, gang=True)

    # ---------- 胡 ----------

    def hu_self(self, seat: int):
        self._require("hu" in self.self_options(seat), "现在不能自摸胡")
        self._settle_hu(seat, zimo=True, from_seat=None, extra_tile=None)
        if len(self.out) >= 3:
            self._finish(draw=False)
        else:
            self._draw(self._next_active(seat))

    def _settle_hu(self, seat: int, zimo: bool, from_seat: int | None,
                   extra_tile: int | None):
        cnt = self._cnt(seat, kind_of(extra_tile) if extra_tile is not None else None)
        f = fan_of(cnt, self.melds[seat], zimo=zimo, gang_flower=self.last_gang_draw and zimo)
        units = 2 ** (f["fan"] - 1)
        if zimo:
            payers = [s for s in self.active() if s != seat]
        else:
            payers = [from_seat]
        for p in payers:
            self.deltas[p] -= units
            self.deltas[seat] += units
        if extra_tile is not None:
            self.hands[seat].append(extra_tile)  # 点炮的牌并入手牌用于亮牌展示
        self.out.add(seat)
        self.winners.append({"seat": seat, "fan": f["fan"], "names": f["names"],
                             "zimo": zimo, "from_seat": from_seat,
                             "hand": sorted(self.hands[seat]),
                             "units": units * len(payers)})
        self.history.append({"a": "hu", "seat": seat, "fan": f["fan"], "zimo": zimo})
        self.current = None
        self.drawn = None

    # ---------- 终局 ----------

    def _finish(self, draw: bool):
        self.phase = "settled"
        self.current = None
        self.drawn = None
        self.claiming = None
        self.result = {
            "draw": draw,
            "winners": self.winners,
            "deltas": list(self.deltas),
            "hands_left": [sorted(h) for h in self.hands],
            "lacks": list(self.lacks),
        }
