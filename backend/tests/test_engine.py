"""对局状态机测试:叫分、出牌校验、回合流转、结算(春天/炸弹翻倍)、流局重发。"""
import pytest

from app.game.engine import DdzMatch
from conftest import cards_of


def make_deck(seat0: str, seat1: str, seat2: str, bottom: str) -> list[int]:
    deck = cards_of(f"{seat0} {seat1} {seat2} {bottom}")
    assert len(deck) == 54
    return deck


# 地主春天局:seat0 拿满炸弹,农民全程不出
SPRING_DECK = make_deck(
    "2 2 2 2 A A A A K K K K Q Q Q Q J",
    "J J 10 10 10 9 9 9 8 8 8 7 7 7 6 6 6",
    "10 9 8 7 6 5 5 5 5 4 4 4 4 3 3 3 x",
    "3 J X",
)


def fresh(deck=SPRING_DECK, first=0):
    return DdzMatch(deck=list(deck), first_seat=first)


def hand_cards(m, seat, spec):
    """从 seat 手牌里按点数挑出与 spec 对应的真实 card id。"""
    from app.game.cards import rank_of
    want = [rank_of(c) for c in cards_of(spec)]
    pool = list(m.hands[seat])
    out = []
    for r in want:
        c = next(c for c in pool if rank_of(c) == r)
        pool.remove(c)
        out.append(c)
    return out


# ---------- 叫分阶段 ----------

def test_initial_phase_and_hands():
    m = fresh()
    assert m.phase == "calling"
    assert [len(h) for h in m.hands] == [17, 17, 17]
    assert len(m.bottom) == 3


def test_call_wrong_turn_rejected():
    m = fresh(first=0)
    with pytest.raises(ValueError):
        m.call(1, 2)


def test_call_three_becomes_landlord_immediately():
    m = fresh(first=0)
    m.call(0, 3)
    assert m.phase == "playing"
    assert m.landlord == 0 and m.base == 3
    assert len(m.hands[0]) == 20
    assert m.current == 0


def test_call_must_exceed_previous():
    m = fresh(first=0)
    m.call(0, 2)
    with pytest.raises(ValueError):
        m.call(1, 1)
    m.call(1, 0)
    m.call(2, 0)
    assert m.landlord == 0 and m.base == 2


def test_all_pass_redeals():
    m = fresh(first=0)
    old_hands = [list(h) for h in m.hands]
    m.call(0, 0)
    m.call(1, 0)
    m.call(2, 0)
    assert m.phase == "calling"
    assert m.landlord is None
    assert [len(h) for h in m.hands] == [17, 17, 17]
    assert m.hands != old_hands  # 重新发牌


# ---------- 出牌校验 ----------

def playing_match():
    m = fresh(first=0)
    m.call(0, 3)
    return m


def test_play_wrong_turn_rejected():
    m = playing_match()
    with pytest.raises(ValueError):
        m.play(1, [m.hands[1][0]])


def test_play_card_not_in_hand_rejected():
    m = playing_match()
    not_mine = m.hands[1][0]
    with pytest.raises(ValueError):
        m.play(0, [not_mine])


def test_play_invalid_pattern_rejected():
    m = playing_match()
    bad = hand_cards(m, 0, "Q K")  # 不是对子
    with pytest.raises(ValueError):
        m.play(0, bad)


def test_leader_cannot_pass():
    m = playing_match()
    with pytest.raises(ValueError):
        m.pass_(0)


def test_follow_must_beat():
    m = playing_match()
    m.play(0, hand_cards(m, 0, "J"))
    weak = hand_cards(m, 1, "6")
    with pytest.raises(ValueError):
        m.play(1, weak)


def test_two_passes_clear_trick():
    m = playing_match()
    m.play(0, hand_cards(m, 0, "J"))
    m.pass_(1)
    m.pass_(2)
    assert m.current == 0
    assert m.last_pattern is None  # 自由出牌
    m.play(0, hand_cards(m, 0, "3"))  # 可以出更小的牌


# ---------- 结算 ----------

def test_landlord_spring_settlement():
    m = playing_match()  # base=3
    seq = ["2 2 2 2", "A A A A", "K K K K", "Q Q Q Q", "J J", "3", "X"]
    for spec in seq:
        m.play(0, hand_cards(m, 0, spec))
        if m.phase == "playing":
            assert m.current != 0
            m.pass_(1)
            m.pass_(2)
    assert m.phase == "settled"
    r = m.result
    assert r["winner_role"] == "landlord"
    assert r["spring"] is True
    assert r["bombs"] == 4
    # 倍数 = 2^4炸弹 × 2春天 = 32,底分 3
    assert r["multiplier"] == 32
    deltas = r["deltas"]
    assert deltas[0] == 2 * 3 * 32 and deltas[1] == -3 * 32 and deltas[2] == -3 * 32
    assert sum(deltas) == 0


ANTI_SPRING_DECK = make_deck(
    "4 4 5 5 6 6 7 7 8 8 9 9 10 10 J J Q",
    "2 3 3 3 K 4 5 6 7 8 9 10 J Q K A 3",
    "Q Q J 10 9 8 7 6 5 4 2 2 2 A A A K",
    "K x X",
)


def test_farmer_anti_spring_settlement():
    m = DdzMatch(deck=list(ANTI_SPRING_DECK), first_seat=0)
    m.call(0, 1)
    m.call(1, 0)
    m.call(2, 0)
    assert m.landlord == 0 and m.base == 1
    m.play(0, hand_cards(m, 0, "4"))          # 地主只出这一手
    m.play(1, hand_cards(m, 1, "2"))
    m.pass_(2)
    m.pass_(0)
    m.play(1, hand_cards(m, 1, "3 4 5 6 7 8 9 10 J Q K A"))
    m.pass_(2)
    m.pass_(0)
    m.play(1, hand_cards(m, 1, "3 3 3 K"))
    assert m.phase == "settled"
    r = m.result
    assert r["winner_role"] == "farmer"
    assert r["spring"] is True and r["bombs"] == 0
    assert r["multiplier"] == 2
    assert r["deltas"] == [-2 * 1 * 2, 1 * 2, 1 * 2]


def test_no_actions_after_settled():
    m = playing_match()
    for spec in ["2 2 2 2", "A A A A", "K K K K", "Q Q Q Q", "J J", "3", "X"]:
        m.play(0, hand_cards(m, 0, spec))
        if m.phase == "playing":
            m.pass_(1)
            m.pass_(2)
    with pytest.raises(ValueError):
        m.play(1, [m.hands[1][0]])
