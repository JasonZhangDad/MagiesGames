"""斗地主对局状态机 —— 服务端唯一可信源,纯逻辑无 IO。

阶段流转: calling → playing → settled(全员不叫则原地重发,留在 calling)。
客户端发来的操作只是"意图",这里校验合法后才更新状态。
"""
import random

from .cards import deal, new_deck, rank_of
from .patterns import Pattern, beats, detect


class DdzMatch:
    def __init__(self, deck: list[int] | None = None, first_seat: int = 0,
                 rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.first_seat = first_seat
        self.phase = "calling"
        self.landlord: int | None = None
        self.base = 0
        self.result: dict | None = None
        self.redeal_count = 0
        self._setup(deck)

    def _setup(self, deck: list[int] | None = None):
        self.hands, self.bottom = deal(deck or new_deck(self.rng))
        self.calls: list[int | None] = [None, None, None]
        self.current = self.first_seat
        self.last_pattern: Pattern | None = None
        self.last_cards: list[int] = []
        self.last_seat: int | None = None
        self.plays_count = [0, 0, 0]
        self.bombs = 0
        self.history: list[dict] = []  # 操作序列,用于回放/日志

    # ---------- 校验 ----------

    def _require(self, cond: bool, msg: str):
        if not cond:
            raise ValueError(msg)

    def _require_turn(self, seat: int, phase: str):
        self._require(self.phase == phase, f"当前不在{ '叫分' if phase == 'calling' else '出牌' }阶段")
        self._require(seat == self.current, "还没轮到你操作")

    # ---------- 叫分 ----------

    def max_call(self) -> int:
        return max((c for c in self.calls if c), default=0)

    def call(self, seat: int, score: int) -> dict:
        self._require_turn(seat, "calling")
        self._require(score in (0, 1, 2, 3), "叫分只能是 0/1/2/3")
        if score != 0:
            self._require(score > self.max_call(), "叫分必须高于之前的叫分")
        self.calls[seat] = score
        self.history.append({"a": "call", "seat": seat, "score": score})
        if score == 3:
            self._set_landlord(seat, 3)
            return {"event": "landlord", "seat": seat}
        if all(c is not None for c in self.calls):
            best = self.max_call()
            if best == 0:
                self.redeal_count += 1
                self.first_seat = (self.first_seat + 1) % 3
                self._setup()
                return {"event": "redeal"}
            winner = max(range(3), key=lambda s: (self.calls[s] or 0))
            self._set_landlord(winner, best)
            return {"event": "landlord", "seat": winner}
        self.current = (seat + 1) % 3
        return {"event": "called", "seat": seat, "score": score}

    def _set_landlord(self, seat: int, base: int):
        self.landlord = seat
        self.base = base
        self.hands[seat] = sorted(self.hands[seat] + self.bottom, key=rank_of)
        self.phase = "playing"
        self.current = seat
        self.last_pattern = None
        self.last_seat = None

    # ---------- 出牌 ----------

    def role_of(self, seat: int) -> str:
        return "landlord" if seat == self.landlord else "farmer"

    def is_leading(self) -> bool:
        return self.last_pattern is None

    def play(self, seat: int, cards: list[int]) -> dict:
        self._require_turn(seat, "playing")
        hand = self.hands[seat]
        self._require(len(set(cards)) == len(cards) and all(c in hand for c in cards),
                      "出的牌不在你的手牌里")
        pattern = detect(cards)
        self._require(pattern is not None, "不是合法牌型")
        if not self.is_leading():
            self._require(beats(pattern, self.last_pattern), "这手牌压不过上家")
        for c in cards:
            hand.remove(c)
        self.plays_count[seat] += 1
        if pattern.kind in ("bomb", "rocket"):
            self.bombs += 1
        self.last_pattern = pattern
        self.last_cards = sorted(cards, key=rank_of)
        self.last_seat = seat
        self.history.append({"a": "play", "seat": seat, "cards": self.last_cards,
                             "kind": pattern.kind})
        if not hand:
            self._settle(seat)
            return {"event": "settled", "pattern": pattern}
        self.current = (seat + 1) % 3
        return {"event": "played", "pattern": pattern}

    def pass_(self, seat: int) -> dict:
        self._require_turn(seat, "playing")
        self._require(not self.is_leading(), "轮到你自由出牌,不能不出")
        self.history.append({"a": "pass", "seat": seat})
        self.current = (seat + 1) % 3
        if self.current == self.last_seat:  # 两家都不要,清空牌权
            self.last_pattern = None
            self.last_cards = []
        return {"event": "passed", "seat": seat}

    # ---------- 结算 ----------

    def _settle(self, winner_seat: int):
        self.phase = "settled"
        winner_role = self.role_of(winner_seat)
        farmers = [s for s in range(3) if s != self.landlord]
        if winner_role == "landlord":
            spring = all(self.plays_count[s] == 0 for s in farmers)
        else:
            spring = self.plays_count[self.landlord] == 1
        multiplier = (2 ** self.bombs) * (2 if spring else 1)
        unit = self.base * multiplier
        deltas = [0, 0, 0]
        sign = 1 if winner_role == "landlord" else -1
        deltas[self.landlord] = 2 * unit * sign
        for s in farmers:
            deltas[s] = -unit * sign
        self.result = {
            "winner_seat": winner_seat,
            "winner_role": winner_role,
            "spring": spring,
            "bombs": self.bombs,
            "base": self.base,
            "multiplier": multiplier,
            "deltas": deltas,
            "hands_left": [list(h) for h in self.hands],
        }
