"""牌型识别与比较测试 —— 规划文档附录 E:所有斗地主牌型识别和比较。"""
import pytest

from app.game.patterns import detect, beats
from conftest import cards_of


def kind_of(spec):
    p = detect(cards_of(spec))
    return None if p is None else p.kind


# ---------- 基础牌型识别 ----------

def test_single():
    p = detect(cards_of("7"))
    assert p.kind == "single" and p.key == 7


def test_pair():
    p = detect(cards_of("Q Q"))
    assert p.kind == "pair" and p.key == 12


def test_pair_mismatch_invalid():
    assert detect(cards_of("Q K")) is None


def test_rocket():
    p = detect(cards_of("x X"))
    assert p.kind == "rocket"


def test_trio():
    p = detect(cards_of("9 9 9"))
    assert p.kind == "trio" and p.key == 9


def test_bomb():
    p = detect(cards_of("5 5 5 5"))
    assert p.kind == "bomb" and p.key == 5


def test_trio_single():
    p = detect(cards_of("7 7 7 K"))
    assert p.kind == "trio_single" and p.key == 7


def test_trio_pair():
    p = detect(cards_of("7 7 7 K K"))
    assert p.kind == "trio_pair" and p.key == 7


def test_trio_pair_with_jokers_invalid():
    # 三带二的"二"必须是对子,大小王不是对
    assert detect(cards_of("7 7 7 x X")) is None


# ---------- 顺子 / 连对 ----------

def test_straight():
    p = detect(cards_of("3 4 5 6 7"))
    assert p.kind == "straight" and p.key == 7 and p.length == 5


def test_straight_to_ace():
    p = detect(cards_of("10 J Q K A"))
    assert p.kind == "straight" and p.key == 14


def test_straight_with_two_invalid():
    assert detect(cards_of("J Q K A 2")) is None


def test_straight_too_short_invalid():
    assert detect(cards_of("3 4 5 6")) is None


def test_straight_long():
    p = detect(cards_of("3 4 5 6 7 8 9 10 J Q K A"))
    assert p.kind == "straight" and p.length == 12


def test_pair_straight():
    p = detect(cards_of("3 3 4 4 5 5"))
    assert p.kind == "pair_straight" and p.key == 5 and p.length == 3


def test_pair_straight_two_pairs_invalid():
    assert detect(cards_of("3 3 4 4")) is None


def test_pair_straight_with_two_invalid():
    assert detect(cards_of("K K A A 2 2")) is None


# ---------- 飞机 ----------

def test_plane_pure():
    p = detect(cards_of("3 3 3 4 4 4"))
    assert p.kind == "plane" and p.key == 4 and p.length == 2


def test_plane_not_consecutive_invalid():
    assert detect(cards_of("3 3 3 5 5 5")) is None


def test_plane_with_two_invalid():
    # 飞机不能包含 2
    assert detect(cards_of("A A A 2 2 2")) is None


def test_plane_single_wings():
    p = detect(cards_of("3 3 3 4 4 4 9 K"))
    assert p.kind == "plane_single" and p.key == 4 and p.length == 2


def test_plane_pair_wings():
    p = detect(cards_of("7 7 7 8 8 8 3 3 5 5"))
    assert p.kind == "plane_pair" and p.key == 8 and p.length == 2


def test_plane_pair_odd_wings_invalid():
    assert detect(cards_of("7 7 7 8 8 8 3 3 5 6")) is None


def test_plane_triple_with_wings():
    p = detect(cards_of("5 5 5 6 6 6 7 7 7 3 4 9"))
    assert p.kind == "plane_single" and p.key == 7 and p.length == 3


# ---------- 四带二 ----------

def test_four_two_singles():
    p = detect(cards_of("9 9 9 9 3 5"))
    assert p.kind == "four_two" and p.key == 9


def test_four_two_pairs():
    p = detect(cards_of("9 9 9 9 3 3 5 5"))
    assert p.kind == "four_two_pair" and p.key == 9


def test_four_with_one_invalid():
    assert detect(cards_of("9 9 9 9 3")) is None


# ---------- 非法散牌 ----------

@pytest.mark.parametrize("spec", ["3 5", "3 4 5", "3 3 4", "3 4 5 6 8", "x x"])
def test_garbage_invalid(spec):
    if spec == "x x":
        with pytest.raises(AssertionError):
            cards_of(spec)
        return
    assert detect(cards_of(spec)) is None


# ---------- 比较 ----------

def b(a_spec, b_spec):
    return beats(detect(cards_of(a_spec)), detect(cards_of(b_spec)))


def test_single_compare():
    assert b("8", "7")
    assert not b("7", "8")
    assert not b("7", "7")


def test_two_beats_ace():
    assert b("2", "A")


def test_joker_beats_two():
    assert b("x", "2") and b("X", "x")


def test_kind_mismatch_no_beat():
    assert not b("8 8", "7")


def test_straight_same_length_only():
    assert b("4 5 6 7 8", "3 4 5 6 7")
    assert not b("4 5 6 7 8 9", "3 4 5 6 7")


def test_bomb_beats_everything_normal():
    assert b("5 5 5 5", "2")
    assert b("5 5 5 5", "A A A K K")
    assert b("6 6 6 6", "5 5 5 5")
    assert not b("5 5 5 5", "6 6 6 6")


def test_rocket_beats_all():
    assert b("x X", "2 2 2 2")
    assert not b("2 2 2 2", "x X")


def test_plane_compare():
    assert b("4 4 4 5 5 5 3 6", "3 3 3 4 4 4 9 K")
