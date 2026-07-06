"""四川麻将胡牌判定与番型测试(万筒条 108 张,无字牌)。

kind 编码:0-8 万1-9,9-17 筒1-9,18-26 条1-9。
"""
from collections import Counter

from app.game.mahjong.tiles import kind_label, new_wall
from app.game.mahjong.win import can_win, fan_of, is_seven_pairs

W = 0    # 万1
T = 9    # 筒1
S = 18   # 条1


def kinds(*ks):
    return Counter(ks)


def test_kind_label_and_wall():
    assert kind_label(0) == "1万"
    assert kind_label(17) == "9筒"
    assert kind_label(26) == "9条"
    assert len(new_wall()) == 108


def test_standard_win_all_sequences():
    # 123万 456万 789万 123筒 + 99条
    h = kinds(W, W + 1, W + 2, W + 3, W + 4, W + 5, W + 6, W + 7, W + 8,
              T, T + 1, T + 2, S + 8, S + 8)
    assert can_win(h)


def test_standard_win_mixed():
    # 111万 234筒 567条 999筒 + 99条
    h = kinds(W, W, W, T + 1, T + 2, T + 3, S + 4, S + 5, S + 6,
              T + 8, T + 8, T + 8, S + 8, S + 8)
    assert can_win(h)


def test_cross_suit_sequence_invalid():
    # 8万9万1筒 不是顺子
    h = kinds(W + 7, W + 8, T, T + 3, T + 4, T + 5, S, S + 1, S + 2,
              S + 6, S + 7, S + 8, W, W)
    assert not can_win(h)


def test_not_win():
    h = kinds(W, W + 1, W + 3, W + 4, T, T + 1, T + 5, S + 2, S + 4,
              S + 6, W + 6, W + 8, T + 8, T + 8)
    assert not can_win(h)


def test_seven_pairs_and_dragon():
    h = kinds(W, W, T, T, S, S, W + 4, W + 4, T + 8, T + 8, S + 8, S + 8, W + 8, W + 8)
    assert is_seven_pairs(h) and can_win(h)
    f = fan_of(h, melds=[], zimo=False)
    assert "七对" in f["names"]
    # 龙七对:含 4 张 1万
    h2 = kinds(W, W, W, W, T, T, S, S, W + 4, W + 4, T + 8, T + 8, S + 8, S + 8)
    assert can_win(h2)
    f2 = fan_of(h2, melds=[], zimo=False)
    assert "龙七对" in f2["names"]


def test_small_hand_win():
    # 碰杠后手牌变短:1 面子 + 1 对
    assert can_win(kinds(W, W + 1, W + 2, S + 8, S + 8))
    assert can_win(kinds(S + 8, S + 8))  # 金钩钓形态的对子


def test_fan_qing_yi_se_zimo():
    h = kinds(W, W + 1, W + 2, W + 3, W + 4, W + 5, W + 6, W + 7, W + 8,
              W, W + 1, W + 2, W + 8, W + 8)
    f = fan_of(h, melds=[], zimo=True)
    assert "清一色" in f["names"] and "自摸" in f["names"]
    assert f["fan"] >= 4


def test_fan_peng_peng_hu():
    h = kinds(W + 1, W + 1, W + 1, S + 8, S + 8)
    melds = [{"kind_id": T, "type": "peng"}, {"kind_id": S + 4, "type": "peng"},
             {"kind_id": W + 4, "type": "peng"}]
    f = fan_of(h, melds=melds, zimo=False)
    assert "碰碰胡" in f["names"]


def test_fan_gang_counts():
    h = kinds(W, W + 1, W + 2, S + 8, S + 8)
    melds = [{"kind_id": T, "type": "angang"}, {"kind_id": S + 4, "type": "gang"},
             {"kind_id": W + 4, "type": "peng"}]
    f = fan_of(h, melds=melds, zimo=False)
    assert f["fan"] >= 3  # 平胡1 + 杠×2


def test_fan_gang_flower():
    h = kinds(W, W + 1, W + 2, S + 8, S + 8)
    f = fan_of(h, melds=[], zimo=True, gang_flower=True)
    assert "杠上开花" in f["names"]
