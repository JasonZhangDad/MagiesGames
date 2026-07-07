"""麻将进阶玩法测试:换三张 + 刮风下雨(杠即时算分)。

刮风下雨规则:直杠放杠者付 2;补杠在场其他各付 1;暗杠在场其他各付 2;
已胡离场者不参与支付。全部计入 deltas,终局保持零和。
"""
import random
from collections import Counter

import pytest

from app.game.mahjong.engine import MahjongMatch
from app.game.mahjong.tiles import kind_of, suit_of
from test_mahjong_engine import fresh, set_all_lacks, hu_ready_hand

W, T, S = 0, 9, 18


# ---------- 换三张 ----------

def pick3(hand: list[int]) -> list[int]:
    """选手里同花色的前 3 张(必存在:13 张 3 花色必有一门 >=5 张)。"""
    by = {}
    for t in hand:
        by.setdefault(suit_of(kind_of(t)), []).append(t)
    tiles = next(v for v in by.values() if len(v) >= 3)
    return tiles[:3]


def test_exchange_off_by_default():
    m = MahjongMatch(rng=random.Random(1))
    assert m.phase == "dingque"


def test_exchange_flow():
    m = MahjongMatch(rng=random.Random(7), exchange=True)
    assert m.phase == "exchange"
    given = []
    for s in range(4):
        sel = pick3(m.hands[s])
        given.append(sel)
        m.set_exchange(s, sel)
    assert m.phase == "dingque"
    assert m.exchange_dir in (1, 2, 3)
    d = m.exchange_dir
    for s in range(4):
        assert len(m.hands[s]) == 13
        recv = (s + d) % 4
        for t in given[s]:
            assert t in m.hands[recv], f"seat{s} 给出的 {t} 应到 seat{recv}"
            assert t not in m.hands[s]


def test_exchange_validation():
    m = MahjongMatch(rng=random.Random(3), exchange=True)
    h = m.hands[0]
    with pytest.raises(ValueError):
        m.set_exchange(0, h[:2])  # 少于 3 张
    mixed = None
    for a in h:
        for b in h:
            if suit_of(kind_of(a)) != suit_of(kind_of(b)):
                third = next(t for t in h if t not in (a, b))
                mixed = [a, b, third]
                break
        if mixed:
            break
    with pytest.raises(ValueError):
        m.set_exchange(0, mixed)  # 花色不同
    with pytest.raises(ValueError):
        m.set_exchange(0, [200, 201, 202])  # 不在手里
    with pytest.raises(ValueError):
        m.set_lack(0, 0)  # 换三张没结束不能定缺
    sel = pick3(h)
    m.set_exchange(0, sel)
    with pytest.raises(ValueError):
        m.set_exchange(0, sel)  # 重复提交


def test_exchange_ai_legal():
    from app.game.mahjong.ai import choose_exchange
    for seed in range(50):
        m = MahjongMatch(rng=random.Random(seed), exchange=True)
        for s in range(4):
            sel = choose_exchange(m.hands[s])
            assert len(sel) == 3
            assert len({suit_of(kind_of(t)) for t in sel}) == 1
            assert all(t in m.hands[s] for t in sel)
            m.set_exchange(s, sel)
    assert m.phase == "dingque"


# ---------- 刮风下雨 ----------

PENG_BAIT = T + 4


def test_zhigang_pays_2_from_discarder():
    h1 = [PENG_BAIT, PENG_BAIT, PENG_BAIT, W, W + 2, W + 4, W + 6,
          T, T + 1, T + 6, T + 7, T + 8, W + 5]
    m = fresh([None, h1, None, None], wall_kinds=[PENG_BAIT])
    set_all_lacks(m, {1: 2})
    m.discard(0, m.drawn)
    m.claim(1, "gang")
    assert m.deltas == [-2, 2, 0, 0]
    assert m.last_gang_pay == {"type": "zhigang", "seat": 1, "units": 2, "payers": [0]}


def test_angang_pays_2_each():
    h0 = [W + 5, W + 5, W + 5, W, W + 2, W + 4, W + 6,
          T, T + 1, T + 6, T + 7, T + 8, T + 3]
    m = fresh([h0, None, None, None], wall_kinds=[W + 5])
    set_all_lacks(m, {0: 2})
    m.angang(0, W + 5)
    assert m.deltas == [6, -2, -2, -2]
    assert m.last_gang_pay["type"] == "angang" and m.last_gang_pay["units"] == 6


def test_bugang_pays_1_each():
    h1 = [PENG_BAIT, PENG_BAIT, W, W + 2, W + 4, W + 6, W + 8,
          T, T + 1, T + 6, T + 7, T + 8, W + 5]
    m = fresh([None, h1, None, None],
              wall_kinds=[PENG_BAIT, W + 3, S + 4, S + 5, PENG_BAIT])
    set_all_lacks(m, {1: 2})
    m.discard(0, m.drawn)  # 打 5筒
    m.claim(1, "peng")
    assert m.deltas == [0, 0, 0, 0]  # 碰不算分
    m.discard(1, m.hands[1][0])
    m.discard(2, m.drawn)
    m.discard(3, m.drawn)
    assert m.current == 0
    m.discard(0, m.drawn)
    # seat1 摸到第 4 张 5筒 → 补杠
    assert kind_of(m.drawn) == PENG_BAIT
    m.bugang(1, PENG_BAIT)
    assert m.deltas == [-1, 3, -1, -1]


def test_out_player_does_not_pay_gang():
    h0 = [T + 5, T + 5, T + 5, T + 3, W, W + 2, W + 4, W + 6,
          T, T + 2, T + 4, T + 6, T + 8]
    m = fresh([h0, hu_ready_hand(), None, None],
              wall_kinds=[T + 2, S + 3, S + 4, T + 5])
    set_all_lacks(m, {0: 2, 1: 2})
    m.discard(0, m.drawn)  # 庄家摸 3筒 打出,seat1 胡
    m.claim(1, "hu")
    base = list(m.deltas)
    assert 1 in m.out and m.current == 2
    m.discard(2, m.drawn)
    m.discard(3, m.drawn)
    # seat0 摸到第 4 张 6筒 → 暗杠,seat1 已胡不付
    assert kind_of(m.drawn) == T + 5
    m.angang(0, T + 5)
    diff = [m.deltas[i] - base[i] for i in range(4)]
    assert diff == [4, 0, -2, -2]
    assert sum(m.deltas) == 0


def test_full_sim_with_exchange_and_gang_pay():
    from app.game.mahjong.ai import (choose_claim, choose_exchange, choose_lack,
                                     choose_self_action)
    for seed in range(100):
        rng = random.Random(seed)
        m = MahjongMatch(rng=rng, dealer=seed % 4, exchange=True)
        for s in range(4):
            m.set_exchange(s, choose_exchange(m.hands[s]))
        for s in range(4):
            m.set_lack(s, choose_lack(m.hands[s]))
        steps = 0
        while m.phase == "playing":
            steps += 1
            assert steps < 3000
            if m.claiming:
                for s in list(m.claiming["options"]):
                    if s not in m.claiming["responses"]:
                        m.claim(s, choose_claim(m, s))
                continue
            seat = m.current
            action, arg = choose_self_action(m, seat)
            if action == "hu":
                m.hu_self(seat)
            elif action == "angang":
                m.angang(seat, arg)
            elif action == "bugang":
                m.bugang(seat, arg)
            else:
                m.discard(seat, arg)
        assert m.phase == "settled"
        assert sum(m.deltas) == 0
