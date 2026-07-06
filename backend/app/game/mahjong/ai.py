"""四川麻将 AI:定缺、出牌、碰杠胡响应。入门级规则+权重,优先保证合法不卡局。

同一套函数服务于:机器人补位、玩家托管、超时代打。
"""
from collections import Counter

from .tiles import kind_of, suit_of


def choose_lack(hand: list[int]) -> int:
    """定缺:选手里张数最少的花色。"""
    by_suit = Counter(suit_of(kind_of(t)) for t in hand)
    return min(range(3), key=lambda s: (by_suit.get(s, 0), s))


def _usefulness(kind: int, cnt: Counter) -> float:
    """一张牌对牌型的价值:成对/成刻加分,邻近连张加分。"""
    v = (cnt[kind] - 1) * 2.6
    for d, w in ((1, 1.0), (2, 0.5)):
        for kk in (kind - d, kind + d):
            if suit_of(kind) == suit_of(max(0, min(26, kk))) and cnt.get(kk, 0):
                v += w
    return v


def choose_discard(match, seat: int) -> int:
    """优先打缺门牌(大到小),其次打孤张废牌。"""
    hand = match.hands[seat]
    lack = match.lacks[seat]
    lack_tiles = [t for t in hand if suit_of(kind_of(t)) == lack]
    if lack_tiles:
        return max(lack_tiles, key=lambda t: kind_of(t) % 9)
    cnt = Counter(kind_of(t) for t in hand)
    return min(hand, key=lambda t: (_usefulness(kind_of(t), cnt), kind_of(t)))


def choose_claim(match, seat: int) -> str:
    """响应别人打出的牌:能胡就胡;碰/杠仅当不拆搭子且非缺门。"""
    opts = match.claiming["options"].get(seat, [])
    if "hu" in opts:
        return "hu"
    kind = kind_of(match.claiming["tile"])
    cnt = Counter(kind_of(t) for t in match.hands[seat])
    if "gang" in opts:
        return "gang"
    if "peng" in opts:
        # 碰完还得有牌打:手里若全是关键搭子就放过
        neighbors = sum(1 for kk in (kind - 2, kind - 1, kind + 1, kind + 2)
                        if suit_of(max(0, min(26, kk))) == suit_of(kind) and cnt.get(kk, 0))
        if cnt[kind] >= 2 and neighbors <= 1 and len(match.hands[seat]) > 4:
            return "peng"
    return "pass"


def choose_self_action(match, seat: int) -> tuple[str, int | None]:
    """自己回合:胡 > 暗杠 > 补杠 > 打牌。返回 (action, arg)。"""
    opts = match.self_options(seat)
    if opts.get("hu"):
        return "hu", None
    if opts.get("angang"):
        k = opts["angang"][0]
        if suit_of(k) != match.lacks[seat]:
            return "angang", k
    if opts.get("bugang"):
        return "bugang", opts["bugang"][0]
    return "discard", choose_discard(match, seat)
