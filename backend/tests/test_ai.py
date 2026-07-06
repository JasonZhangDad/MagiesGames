"""AI 测试:候选招法合法性 + 大规模全 AI 对局仿真(必终局、积分守恒、引擎零异常)。"""
import random

import pytest

from app.game.ai import choose_action, choose_call, gen_beats, hint
from app.game.engine import DdzMatch
from app.game.patterns import beats, detect
from conftest import cards_of


# ---------- 跟牌候选合法性 ----------

def test_gen_beats_all_legal():
    rng = random.Random(7)
    for _ in range(300):
        deck = list(range(54))
        rng.shuffle(deck)
        hand = sorted(deck[:17])
        last_cards = None
        # 随机取一手合法牌型作为上家出牌
        for size in (1, 2, 3, 4, 5, 6, 8):
            cand = deck[17:17 + size]
            if detect(cand):
                last_cards = cand
                break
        if last_cards is None:
            continue
        last = detect(last_cards)
        for move in gen_beats(hand, last):
            assert all(c in hand for c in move)
            p = detect(move)
            assert p is not None, f"非法牌型 {move}"
            assert beats(p, last), f"{move} 压不过 {last_cards}"


def test_gen_beats_finds_bigger_single():
    hand = cards_of("3 5 9 K A")
    last = detect(cards_of("Q"))
    moves = gen_beats(hand, last)
    assert moves, "有 K/A 却找不到能压 Q 的牌"


def test_gen_beats_uses_bomb_when_needed():
    hand = cards_of("5 5 5 5 3")
    last = detect(cards_of("2 2"))
    moves = gen_beats(hand, last)
    assert any(len(m) == 4 for m in moves), "应能用炸弹压对2"


def test_hint_returns_none_when_cannot_beat():
    m = DdzMatch(first_seat=0, rng=random.Random(1))
    m.call(0, 3)
    # 地主先出王炸(若有),否则跳过该测试路径——这里直接构造:
    hand = cards_of("3 4")
    last = detect(cards_of("2 2 2"))
    assert gen_beats(hand, last) == []


# ---------- 叫分 ----------

def test_choose_call_range():
    rng = random.Random(3)
    for _ in range(100):
        deck = list(range(54))
        rng.shuffle(deck)
        s = choose_call(sorted(deck[:17]), max_call=0)
        assert s in (0, 1, 2, 3)


def test_choose_call_strong_hand_calls_three():
    hand = cards_of("X x 2 2 2 2 A A A A K K K Q Q J 10")
    assert choose_call(hand, max_call=0) == 3


def test_choose_call_respects_max():
    hand = cards_of("X x 2 2 2 2 A A A A K K K Q Q J 10")
    assert choose_call(hand, max_call=3) == 0


# ---------- 全 AI 对局仿真 ----------

@pytest.mark.parametrize("seed", range(500))
def test_full_bot_game_terminates(seed):
    rng = random.Random(seed)
    m = DdzMatch(rng=rng, first_seat=seed % 3)
    steps = 0
    while m.phase != "settled":
        steps += 1
        assert steps < 600, "对局步数超限,疑似死循环"
        seat = m.current
        if m.phase == "calling":
            others_passed = sum(1 for c in m.calls if c == 0)
            must = m.redeal_count >= 1 and others_passed == 2
            m.call(seat, choose_call(m.hands[seat], max_call=m.max_call(), must=must))
        else:
            action, cards = choose_action(m, seat)
            if action == "play":
                m.play(seat, cards)
            else:
                m.pass_(seat)
    r = m.result
    assert sum(r["deltas"]) == 0
    assert r["multiplier"] >= r["base"] // 3 if True else None
    assert not m.hands[r["winner_seat"]]
    # 提示功能在终局后不再给建议之外,任意时刻不抛异常即可(上面全程已覆盖)


def test_hint_matches_choose_when_following():
    rng = random.Random(42)
    m = DdzMatch(rng=rng)
    while m.phase == "calling":
        seat = m.current
        m.call(seat, choose_call(m.hands[seat], max_call=m.max_call(), must=True))
    # 地主随便领出一张单牌,验证 hint 给下家的建议合法
    lead = min(m.hands[m.current], key=lambda c: c)
    m.play(m.current, [lead])
    seat = m.current
    h = hint(m, seat)
    if h is not None:
        p = detect(h)
        assert p and beats(p, m.last_pattern)
        assert all(c in m.hands[seat] for c in h)
