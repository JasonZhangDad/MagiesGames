"""中国象棋引擎测试。坐标 x∈[0,8] y∈[0,9],红方在下(y0 为红底线),红先。

side: 0 红 / 1 黑;board[y][x] = None 或 (side, kind);
kind: k帅 a士 b相 n马 r车 c炮 p兵。
"""
import random

import pytest

from app.game.xiangqi.engine import XiangqiMatch


def empty_with(pieces, turn_side=0, red_seat=0):
    """pieces: [(x, y, side, kind)];必须含双方 k。"""
    board = [[None] * 9 for _ in range(10)]
    for x, y, side, kind in pieces:
        board[y][x] = (side, kind)
    return XiangqiMatch(red_seat=red_seat, board=board, turn_side=turn_side)


KINGS = [(4, 0, 0, "k"), (3, 9, 1, "k")]  # 不同线,避免对脸


# ---------- 初始局面 ----------

def test_initial_setup_and_turn():
    m = XiangqiMatch(red_seat=0)
    assert m.phase == "playing" and m.current == 0
    assert m.board[0][0] == (0, "r") and m.board[0][4] == (0, "k")
    assert m.board[2][1] == (0, "c") and m.board[3][0] == (0, "p")
    assert m.board[9][8] == (1, "r") and m.board[9][4] == (1, "k")
    assert m.board[7][7] == (1, "c") and m.board[6][8] == (1, "p")
    assert sum(1 for row in m.board for c in row if c) == 32


def test_red_moves_first_and_alternates():
    m = XiangqiMatch(red_seat=1)  # seat1 执红
    assert m.current == 1
    m.move(1, (0, 3), (0, 4))  # 红兵进一
    assert m.current == 0
    with pytest.raises(ValueError):
        m.move(1, (2, 3), (2, 4))  # 没轮到


# ---------- 各兵种走法 ----------

def test_horse_leg_block():
    m = empty_with(KINGS + [(4, 4, 0, "n"), (4, 5, 1, "p")], turn_side=0)
    # 马腿在 (4,5) 被卒别住 → 不能往 (3,6)/(5,6)
    with pytest.raises(ValueError):
        m.move(0, (4, 4), (3, 6))
    m.move(0, (4, 4), (6, 5))  # 横日无腿,可走


def test_elephant_eye_and_river():
    m = empty_with(KINGS + [(2, 0, 0, "b"), (3, 1, 1, "p")], turn_side=0)
    with pytest.raises(ValueError):
        m.move(0, (2, 0), (4, 2))  # 象眼 (3,1) 被塞
    m2 = empty_with(KINGS + [(2, 4, 0, "b")], turn_side=0)
    with pytest.raises(ValueError):
        m2.move(0, (2, 4), (4, 6))  # 相不能过河
    m2.move(0, (2, 4), (0, 2))


def test_advisor_and_king_palace():
    m = empty_with(KINGS + [(3, 0, 0, "a")], turn_side=0)
    with pytest.raises(ValueError):
        m.move(0, (3, 0), (2, 1))  # 士出九宫
    m.move(0, (3, 0), (4, 1))
    m2 = empty_with(KINGS, turn_side=0)
    with pytest.raises(ValueError):
        m2.move(0, (4, 0), (5, 1))  # 帅走斜线
    with pytest.raises(ValueError):
        m2.move(0, (4, 0), (4, 3))  # 帅一次多步


def test_cannon_screen_rules():
    m = empty_with(KINGS + [(4, 2, 0, "c"), (4, 5, 1, "p"), (4, 7, 1, "r")], turn_side=0)
    m.move(0, (4, 2), (4, 7))  # 隔一个炮架吃车
    assert m.board[7][4] == (0, "c")
    m2 = empty_with(KINGS + [(0, 2, 0, "c"), (0, 5, 1, "p")], turn_side=0)
    with pytest.raises(ValueError):
        m2.move(0, (0, 2), (0, 5))  # 无架不能吃紧邻目标后…这里其实是隔0子吃,非法
    with pytest.raises(ValueError):
        m2.move(0, (0, 2), (0, 7))  # 越过棋子不吃(平移被挡)
    m2.move(0, (0, 2), (0, 4))  # 平移到空位合法


def test_pawn_river_rules():
    m = empty_with(KINGS + [(2, 4, 0, "p")], turn_side=0)
    with pytest.raises(ValueError):
        m.move(0, (2, 4), (1, 4))  # 未过河不能横走
    with pytest.raises(ValueError):
        m.move(0, (2, 4), (2, 3))  # 不能后退
    m.move(0, (2, 4), (2, 5))  # 过河
    m.move(1, (3, 9), (3, 8))  # 黑随便动
    m.move(0, (2, 5), (3, 5))  # 过河后可横走


def test_flying_general_forbidden():
    # 双帅同列中间只有一子,该子不能走开
    m = empty_with([(4, 0, 0, "k"), (4, 9, 1, "k"), (4, 5, 0, "r")], turn_side=0)
    with pytest.raises(ValueError):
        m.move(0, (4, 5), (5, 5))  # 车走开 → 对脸,非法
    m.move(0, (4, 5), (4, 8))  # 沿列走仍挡着,合法


# ---------- 将军与终局 ----------

def test_must_resolve_check():
    # 黑车将军,红必须应将
    m = empty_with(KINGS + [(4, 5, 1, "r"), (0, 0, 0, "r")], turn_side=0)
    assert m.in_check(0)
    with pytest.raises(ValueError):
        m.move(0, (0, 0), (0, 1))  # 不应将非法
    m.move(0, (4, 0), (5, 0))  # 帅避将(3 列会与黑将对脸)


def test_checkmate_ends_game():
    # 红只剩帅 (4,0);黑三车封 3/4/5 三列 → 黑随便动一步后红无合法着法,绝杀
    m = empty_with([(4, 0, 0, "k"), (4, 9, 1, "k"),
                    (3, 5, 1, "r"), (4, 5, 1, "r"), (5, 5, 1, "r")],
                   turn_side=1)
    m.move(1, (3, 5), (3, 4))  # 仍控 3 列
    assert m.phase == "settled"
    assert m.result["winner_seat"] == 1
    assert sum(m.result["deltas"]) == 0


def test_stalemate_is_loss_v2():
    m = empty_with([(3, 0, 0, "k"), (4, 9, 1, "k"),
                    (4, 5, 1, "r"), (0, 1, 1, "r")],
                   turn_side=1)
    m.move(1, (0, 1), (1, 1))  # 黑车平一,红帅 (3,0):上 (3,1) 有车行控制,右 (4,0) 有 4 列车 → 困毙
    assert m.phase == "settled"
    assert m.result["winner_seat"] == 1


def test_no_capture_draw():
    m = empty_with(KINGS + [(0, 0, 0, "r"), (8, 9, 1, "r")], turn_side=0)
    moves0 = [((0, 0), (1, 0)), ((1, 0), (0, 0))]
    moves1 = [((8, 9), (7, 9)), ((7, 9), (8, 9))]
    i = 0
    while m.phase == "playing" and i < 200:
        m.move(0, *moves0[i % 2])
        if m.phase != "playing":
            break
        m.move(1, *moves1[i % 2])
        i += 1
    assert m.phase == "settled"
    assert m.result["winner_seat"] is None  # 60 回合无吃子判和


# ---------- AI ----------

def test_ai_takes_free_rook():
    from app.game.xiangqi.ai import choose_move
    m = empty_with(KINGS + [(0, 0, 0, "r"), (0, 5, 1, "r")], turn_side=0)
    frm, to = choose_move(m, 0)
    m.move(0, frm, to)
    # 白吃车(或至少不丢子):吃车是唯一大分行动
    assert m.board[5][0] == (0, "r") or m.result


def test_ai_escapes_check():
    from app.game.xiangqi.ai import choose_move
    m = empty_with(KINGS + [(4, 5, 1, "r"), (0, 3, 0, "r")], turn_side=0)
    assert m.in_check(0)
    frm, to = choose_move(m, 0)
    m.move(0, frm, to)  # 合法应将
    assert not m.in_check(0)


@pytest.mark.parametrize("seed", range(8))
def test_full_ai_game_terminates(seed):
    from app.game.xiangqi.ai import choose_move
    rng = random.Random(seed)
    m = XiangqiMatch(red_seat=seed % 2, rng=rng)
    steps = 0
    while m.phase == "playing":
        steps += 1
        assert steps < 4000
        frm, to = choose_move(m, m.current)
        m.move(m.current, frm, to)
    assert m.phase == "settled"
    assert sum(m.result["deltas"]) == 0
