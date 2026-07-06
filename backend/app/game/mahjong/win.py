"""四川麻将胡牌判定与番型(推倒胡计番:平胡/七对/碰碰胡/清一色/杠/自摸/杠上开花)。

缺一门在引擎层校验(定缺花色不能出现在手牌+副露)。输入是 kind 计数 Counter。
"""
from collections import Counter
from functools import lru_cache

from .tiles import suit_of


def _counts_key(cnt: Counter) -> tuple:
    return tuple(sorted((k, c) for k, c in cnt.items() if c > 0))


@lru_cache(maxsize=65536)
def _decompose(key: tuple) -> bool:
    """剩余牌能否全部拆成面子(刻子/顺子)。"""
    if not key:
        return True
    cnt = dict(key)
    k = min(cnt)
    if cnt[k] >= 3:
        nxt = dict(cnt)
        nxt[k] -= 3
        if nxt[k] == 0:
            del nxt[k]
        if _decompose(tuple(sorted(nxt.items()))):
            return True
    if k % 9 <= 6 and cnt.get(k + 1, 0) > 0 and cnt.get(k + 2, 0) > 0 \
            and suit_of(k) == suit_of(k + 2):
        nxt = dict(cnt)
        for kk in (k, k + 1, k + 2):
            nxt[kk] -= 1
            if nxt[kk] == 0:
                del nxt[kk]
        if _decompose(tuple(sorted(nxt.items()))):
            return True
    return False


def is_seven_pairs(cnt: Counter) -> bool:
    return sum(cnt.values()) == 14 and all(c in (2, 4) for c in cnt.values()) \
        and sum(2 if c == 4 else 1 for c in cnt.values()) == 7


def can_win(cnt: Counter) -> bool:
    """标准型(n 面子 + 1 对)或七对。cnt 总张数需为 3n+2。"""
    total = sum(cnt.values())
    if total % 3 != 2:
        return False
    if is_seven_pairs(cnt):
        return True
    for pair in [k for k, c in cnt.items() if c >= 2]:
        rest = cnt.copy()
        rest[pair] -= 2
        if _decompose(_counts_key(rest)):
            return True
    return False


def _all_triplet_win(cnt: Counter, melds: list[dict]) -> bool:
    """碰碰胡:副露全是碰/杠,手牌拆成刻子 + 一对。"""
    if any(m["type"] not in ("peng", "gang", "angang", "bugang") for m in melds):
        return False
    pairs = [k for k, c in cnt.items() if c == 2]
    if len(pairs) != 1:
        return False
    rest = cnt.copy()
    rest[pairs[0]] -= 2
    return all(c == 3 for c in (+rest).values())


def fan_of(cnt: Counter, melds: list[dict], zimo: bool,
           gang_flower: bool = False) -> dict:
    """计番。返回 {"fan": n, "names": [...]}。上限 6 番。"""
    names = []
    fan = 1
    if is_seven_pairs(cnt):
        # 龙七对:七对含 4 张同牌
        if any(c == 4 for c in cnt.values()):
            names.append("龙七对")
            fan += 2
        else:
            names.append("七对")
            fan += 1
    elif _all_triplet_win(cnt, melds):
        names.append("碰碰胡")
        fan += 1
    else:
        names.append("平胡")
    suits = {suit_of(k) for k in cnt} | {suit_of(m["kind_id"]) for m in melds}
    if len(suits) == 1:
        names.append("清一色")
        fan += 2
    gangs = sum(1 for m in melds if m["type"] in ("gang", "angang", "bugang"))
    if gangs:
        names.append(f"杠×{gangs}")
        fan += gangs
    if zimo:
        names.append("自摸")
        fan += 1
    if gang_flower:
        names.append("杠上开花")
        fan += 1
    return {"fan": min(fan, 6), "names": names}
