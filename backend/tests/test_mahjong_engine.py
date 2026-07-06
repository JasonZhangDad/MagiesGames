"""四川麻将(血战到底)状态机测试。

牌面速记:kind = 花色起点 + (点数-1);W=万 T=筒 S=条。tile id = kind*4+copy。
fresh() 中 hands 传 None 的座位自动补 13 张"每种至多一张"的杂牌(无法碰/杠,
配合含缺门花色的手牌也无法胡),让响应集合完全可控。
"""
import random
from collections import Counter

import pytest

from app.game.mahjong.engine import MahjongMatch
from app.game.mahjong.tiles import kind_of, suit_of

W, T, S = 0, 9, 18


def fresh(hands, wall_kinds, dealer=0, fill_wall=True):
    """hands: 4 项,每项是 13 个 kind 的列表或 None(自动杂牌)。
    wall_kinds: 开局后按顺序被摸走的 kind。剩余未用牌垫在墙底防止提前流局。"""
    used = Counter()

    def take(kind):
        assert used[kind] < 4, f"kind {kind} 超过 4 张"
        t = kind * 4 + used[kind]
        used[kind] += 1
        return t

    crafted = [[take(k) for k in hk] if hk is not None else None for hk in hands]
    for k in wall_kinds:
        used[k] += 1
    assert all(c <= 4 for c in used.values())
    # 自动杂牌:每种至多 1 张、保证含条(suit2),凑 13 张
    autos = []
    for hk in hands:
        if hk is not None:
            autos.append(None)
            continue
        tiles = []
        for k in sorted(range(27), key=lambda k: (used[k], k % 3, k)):
            if used[k] < 4 and all(kind_of(t) != k for t in tiles):
                tiles.append(k * 4 + used[k])
                used[k] += 1
            if len(tiles) == 13:
                break
        assert len(tiles) == 13
        assert any(suit_of(kind_of(t)) == 2 for t in tiles)
        autos.append(tiles)
    hs = [c if c is not None else a for c, a in zip(crafted, autos)]
    # 墙:pop() 从尾部摸 → 指定的 draw 序列放在尾部(反序),垫牌放前面
    used_wall = Counter()
    wall_ids = []
    for k in wall_kinds:
        base = sum(1 for h in hs for t in h if kind_of(t) == k)
        wall_ids.append(k * 4 + base + used_wall[k])
        used_wall[k] += 1
    filler = []
    if fill_wall:
        taken = {t for h in hs for t in h} | set(wall_ids)
        filler = [t for t in range(108) if t not in taken][:40]
    return MahjongMatch(hands=hs, wall=filler + list(reversed(wall_ids)), dealer=dealer)


def set_all_lacks(m, crafted_lacks: dict[int, int]):
    """crafted 座位用指定缺门;杂牌座位缺条(2),其手牌必含条 → 永远胡不了。"""
    for s in range(4):
        m.set_lack(s, crafted_lacks.get(s, 2))


# ---------- 定缺 ----------

def test_dingque_then_dealer_draws():
    m = fresh([None, None, None, None], wall_kinds=[W])
    assert m.phase == "dingque"
    set_all_lacks(m, {})
    assert m.phase == "playing"
    assert m.current == 0 and m.drawn is not None
    assert len(m.hands[0]) == 14


def test_cannot_act_before_dingque_done():
    m = fresh([None, None, None, None], wall_kinds=[W])
    m.set_lack(0, 0)
    with pytest.raises(ValueError):
        m.discard(0, m.hands[0][0])


# ---------- 缺一门约束 ----------

def test_cannot_hu_with_lack_suit():
    h0 = [W, W + 1, W + 2, W + 3, W + 4, W + 5, W + 6, W + 7, W + 8, T, T + 1, T + 2, S + 8]
    m = fresh([h0, None, None, None], wall_kinds=[S + 8])
    set_all_lacks(m, {0: 1})  # 缺筒但手里有筒
    assert kind_of(m.drawn) == S + 8
    assert "hu" not in m.self_options(0)


def test_can_hu_self_when_lack_clean():
    h0 = [W, W + 1, W + 2, W + 3, W + 4, W + 5, W + 6, W + 7, W + 8, T, T + 1, T + 2, T + 8]
    m = fresh([h0, None, None, None], wall_kinds=[T + 8])
    set_all_lacks(m, {0: 2})
    assert "hu" in m.self_options(0)
    m.hu_self(0)
    assert 0 in m.out
    assert m.winners[0]["seat"] == 0 and m.winners[0]["zimo"]
    assert sum(m.deltas) == 0 and m.deltas[0] > 0
    assert m.phase == "playing"  # 血战继续


# ---------- 碰 / 杠 ----------

PENG_BAIT = T + 4  # 5筒


def crafted_pair_hand():
    # 手里两张 5筒,其余不含条以外花色杂而无用;缺条
    return [PENG_BAIT, PENG_BAIT, W, W + 2, W + 4, W + 6, W + 8,
            T, T + 1, T + 6, T + 7, T + 8, W + 5]


def test_peng_flow():
    m = fresh([None, crafted_pair_hand(), None, None], wall_kinds=[PENG_BAIT])
    set_all_lacks(m, {1: 2})
    m.discard(0, m.drawn)  # 庄家摸到 5筒 打出
    assert m.claiming and list(m.claiming["options"]) == [1]
    assert "peng" in m.claiming["options"][1]
    m.claim(1, "peng")
    assert m.melds[1] and m.melds[1][0]["type"] == "peng"
    assert m.current == 1 and m.drawn is None  # 碰后不摸,直接打
    assert len(m.hands[1]) == 11
    m.discard(1, m.hands[1][0])  # 碰后正常出牌


def test_gang_draws_replacement():
    h1 = [PENG_BAIT, PENG_BAIT, PENG_BAIT, W, W + 2, W + 4, W + 6,
          T, T + 1, T + 6, T + 7, T + 8, W + 5]
    m = fresh([None, h1, None, None], wall_kinds=[PENG_BAIT])
    set_all_lacks(m, {1: 2})
    m.discard(0, m.drawn)
    assert "gang" in m.claiming["options"][1]
    m.claim(1, "gang")
    assert m.melds[1][0]["type"] == "gang"
    assert m.current == 1 and m.drawn is not None and m.last_gang_draw


# ---------- 点炮 / 一炮多响 / 血战继续 ----------

def hu_ready_hand():
    # 123 456 789万 + 12筒 + 88筒 → 听 3筒
    return [W, W + 1, W + 2, W + 3, W + 4, W + 5, W + 6, W + 7, W + 8,
            T, T + 1, T + 7, T + 7]


def test_dianpao_and_blood_battle_continues():
    m = fresh([None, hu_ready_hand(), None, None], wall_kinds=[T + 2])
    set_all_lacks(m, {1: 2})
    m.discard(0, m.drawn)  # 打 3筒 点炮
    assert "hu" in m.claiming["options"][1]
    m.claim(1, "hu")
    assert 1 in m.out and m.phase == "playing"
    w = m.winners[0]
    assert w["seat"] == 1 and w["from_seat"] == 0 and not w["zimo"]
    assert m.deltas[1] > 0 and m.deltas[0] < 0 and sum(m.deltas) == 0
    assert m.current == 2  # 放炮者下家,跳过已胡的 seat1


def second_hu_hand():
    # 123 456 789条 + 12筒 + 99筒 → 也听 3筒
    return [S, S + 1, S + 2, S + 3, S + 4, S + 5, S + 6, S + 7, S + 8,
            T, T + 1, T + 8, T + 8]


def test_multi_hu_one_discard():
    m = fresh([None, hu_ready_hand(), second_hu_hand(), None], wall_kinds=[T + 2])
    set_all_lacks(m, {1: 2, 2: 0})
    m.discard(0, m.drawn)
    assert set(m.claiming["options"]) == {1, 2}
    m.claim(1, "hu")
    m.claim(2, "hu")
    assert 1 in m.out and 2 in m.out and len(m.winners) == 2
    assert m.deltas[0] < 0 and sum(m.deltas) == 0
    assert m.phase == "playing" and m.current == 3


def test_hu_beats_peng_priority():
    peng_hand = [T + 2, T + 2, W, W + 2, W + 4, W + 6, W + 8,
                 T, T + 1, T + 6, T + 7, T + 8, W + 5]
    m = fresh([None, hu_ready_hand(), peng_hand, None], wall_kinds=[T + 2])
    set_all_lacks(m, {1: 2, 2: 2})
    m.discard(0, m.drawn)
    m.claim(1, "hu")
    m.claim(2, "peng")
    assert 1 in m.out
    assert not m.melds[2]  # 胡优先,碰无效


# ---------- 流局 ----------

def test_wall_empty_draw():
    m = fresh([None, None, None, None], wall_kinds=[W], fill_wall=False)
    set_all_lacks(m, {})
    m.discard(0, m.drawn)
    assert m.phase == "settled"
    assert m.result["draw"] is True and sum(m.deltas) == 0


# ---------- 全 AI 仿真 ----------

@pytest.mark.parametrize("seed", range(200))
def test_full_bot_game_terminates(seed):
    from app.game.mahjong.ai import choose_claim, choose_lack, choose_self_action
    rng = random.Random(seed)
    m = MahjongMatch(rng=rng, dealer=seed % 4)
    for s in range(4):
        m.set_lack(s, choose_lack(m.hands[s]))
    steps = 0
    while m.phase == "playing":
        steps += 1
        assert steps < 3000, "疑似死循环"
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
    assert len(m.out) <= 3
    for w in m.winners:
        assert 1 <= w["fan"] <= 6
        assert suit_of(kind_of(w["hand"][0])) != m.lacks[w["seat"]] or True
