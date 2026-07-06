"""斗地主牌型识别与比较 —— 纯函数,服务端唯一可信的规则核心。"""
from collections import Counter
from dataclasses import dataclass

from .cards import rank_of

CHAIN_MAX = 14  # 顺子/连对/飞机最大到 A,不含 2 和王

KIND_LABEL = {
    "single": "单牌", "pair": "对子", "trio": "三张", "trio_single": "三带一",
    "trio_pair": "三带二", "straight": "顺子", "pair_straight": "连对",
    "plane": "飞机", "plane_single": "飞机带单", "plane_pair": "飞机带对",
    "four_two": "四带二", "four_two_pair": "四带两对", "bomb": "炸弹", "rocket": "王炸",
}


@dataclass(frozen=True)
class Pattern:
    kind: str
    key: int      # 主牌点数,用于同型比较
    length: int   # 链长(顺子张数/连对对数/飞机三张组数),非链型为 1


def _consecutive(ranks: list[int]) -> bool:
    return all(b - a == 1 for a, b in zip(ranks, ranks[1:])) and ranks[-1] <= CHAIN_MAX


def _plane(cnt: Counter, n: int) -> Pattern | None:
    """飞机(纯/带单/带对)。找连续三张组,剩余作为翅膀校验。"""
    trio_ranks = sorted(r for r, c in cnt.items() if c >= 3 and r <= CHAIN_MAX)
    # 枚举所有连续三张组区间,长度 k >= 2
    for size, kind in ((3, "plane"), (4, "plane_single"), (5, "plane_pair")):
        if n % size != 0:
            continue
        k = n // size
        if k < 2:
            continue
        # 从高到低找长度为 k 的连续区间,优先高 key
        for hi_idx in range(len(trio_ranks) - 1, k - 2, -1):
            run = trio_ranks[hi_idx - k + 1:hi_idx + 1]
            if not _consecutive(run):
                continue
            rest = cnt.copy()
            for r in run:
                rest[r] -= 3
            rest = +rest
            total_rest = sum(rest.values())
            if kind == "plane" and total_rest == 0:
                return Pattern(kind, run[-1], k)
            if kind == "plane_single" and total_rest == k:
                return Pattern(kind, run[-1], k)
            if kind == "plane_pair" and total_rest == 2 * k and all(c % 2 == 0 for c in rest.values()) \
                    and all(r <= 15 for r in rest):  # 王不能成对
                return Pattern(kind, run[-1], k)
    return None


def detect(cards: list[int]) -> Pattern | None:
    """识别一手牌的牌型,非法返回 None。"""
    n = len(cards)
    if n == 0 or len(set(cards)) != n:
        return None
    ranks = sorted(rank_of(c) for c in cards)
    cnt = Counter(ranks)
    distinct = sorted(cnt)

    if n == 1:
        return Pattern("single", ranks[0], 1)
    if n == 2:
        if ranks == [16, 17]:
            return Pattern("rocket", 17, 1)
        if cnt[ranks[0]] == 2 and ranks[0] <= 15:
            return Pattern("pair", ranks[0], 1)
        return None
    if n == 3:
        if cnt[ranks[0]] == 3:
            return Pattern("trio", ranks[0], 1)
        return None
    if n == 4:
        if cnt[ranks[0]] == 4:
            return Pattern("bomb", ranks[0], 1)
        if sorted(cnt.values()) == [1, 3]:
            trio = next(r for r, c in cnt.items() if c == 3)
            return Pattern("trio_single", trio, 1)
        return None
    if n == 5 and sorted(cnt.values()) == [2, 3]:
        trio = next(r for r, c in cnt.items() if c == 3)
        pair = next(r for r, c in cnt.items() if c == 2)
        if pair <= 15:
            return Pattern("trio_pair", trio, 1)
        return None

    # 顺子:全单张连续,>=5 张
    if n >= 5 and all(c == 1 for c in cnt.values()) and _consecutive(distinct):
        return Pattern("straight", distinct[-1], n)
    # 连对:全对子连续,>=3 对
    if n >= 6 and n % 2 == 0 and all(c == 2 for c in cnt.values()) and _consecutive(distinct):
        return Pattern("pair_straight", distinct[-1], n // 2)
    # 四带二 / 四带两对
    if n == 6:
        quads = [r for r, c in cnt.items() if c == 4]
        if quads:
            return Pattern("four_two", max(quads), 1)
    if n == 8:
        for quad in sorted((r for r, c in cnt.items() if c == 4), reverse=True):
            rest = cnt.copy()
            rest[quad] -= 4
            rest = +rest
            if all(c % 2 == 0 for c in rest.values()) and all(r <= 15 for r in rest):
                # 剩余 4 张须为两对(含同点四张拆两对的极端情况)
                return Pattern("four_two_pair", quad, 1)
    # 飞机(放在四带二之后,8 张时优先按四带两对解释)
    p = _plane(cnt, n)
    if p:
        return p
    return None


def beats(a: Pattern | None, b: Pattern | None) -> bool:
    """a 是否压过 b。b 为 None 表示自由出牌,任何合法牌型都可以。"""
    if a is None:
        return False
    if b is None:
        return True
    if a.kind == "rocket":
        return True
    if b.kind == "rocket":
        return False
    if a.kind == "bomb":
        return b.kind != "bomb" or a.key > b.key
    if b.kind == "bomb":
        return False
    return a.kind == b.kind and a.length == b.length and a.key > b.key
