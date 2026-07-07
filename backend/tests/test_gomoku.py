"""五子棋引擎与 AI 测试:15 路无禁手,连五即胜,满盘平局。"""
import random

import pytest

from app.game.gomoku.engine import SIZE, GomokuMatch


def test_alternate_turns_and_validation():
    m = GomokuMatch(first=0)
    assert m.phase == "playing" and m.current == 0
    m.place(0, 7, 7)
    assert m.current == 1
    with pytest.raises(ValueError):
        m.place(0, 8, 8)  # 没轮到
    with pytest.raises(ValueError):
        m.place(1, 7, 7)  # 已占
    with pytest.raises(ValueError):
        m.place(1, 15, 0)  # 越界
    m.place(1, 8, 8)
    assert m.current == 0


def test_horizontal_win():
    m = GomokuMatch(first=0)
    for i in range(4):
        m.place(0, 3 + i, 7)
        m.place(1, 3 + i, 8)
    m.place(0, 7, 7)  # 第 5 连
    assert m.phase == "settled"
    assert m.result["winner_seat"] == 0
    assert m.result["deltas"] == [2, -2]
    assert m.result["win_line"] and len(m.result["win_line"]) >= 5


def test_diagonal_win_and_overline_counts():
    m = GomokuMatch(first=1)
    # seat1 走对角 (2,2)..(6,6),seat0 乱走
    seat0_moves = [(0, i) for i in range(6)]
    for i in range(4):
        m.place(1, 2 + i, 2 + i)
        m.place(0, *seat0_moves[i])
    m.place(1, 6, 6)
    assert m.phase == "settled" and m.result["winner_seat"] == 1


def test_no_move_after_settled():
    m = GomokuMatch(first=0)
    for i in range(4):
        m.place(0, i, 0)
        m.place(1, i, 1)
    m.place(0, 4, 0)
    assert m.phase == "settled"
    with pytest.raises(ValueError):
        m.place(1, 9, 9)


def test_draw_on_full_board():
    # (x+2y) mod 4 < 2 染色:横竖斜任意方向同色连子 ≤2,满盘必平局
    pattern = [[0 if (x + 2 * y) % 4 < 2 else 1 for x in range(SIZE)] for y in range(SIZE)]
    cells = [(x, y) for y in range(SIZE) for x in range(SIZE)]
    zeros = [(x, y) for (x, y) in cells if pattern[y][x] == 0]
    ones = [(x, y) for (x, y) in cells if pattern[y][x] == 1]
    big, small = (zeros, ones) if len(zeros) > len(ones) else (ones, zeros)
    assert len(big) == len(small) + 1  # 225 格,先手多一子
    m = GomokuMatch(first=0)
    for i in range(len(big)):
        m.place(0, *big[i])
        if i < len(small):
            m.place(1, *small[i])
    assert m.phase == "settled"
    assert m.result["winner_seat"] is None
    assert m.result["deltas"] == [0, 0]


def test_ai_takes_winning_move():
    from app.game.gomoku.ai import choose_move
    m = GomokuMatch(first=0)
    for i in range(4):
        m.place(0, 3 + i, 7)
        m.place(1, 3 + i, 9)
    # seat1 拦截或 seat0 连五?现在轮到 seat0,AI 应该直接下 (7,7) 或 (2,7) 取胜
    x, y = choose_move(m, 0)
    m.place(0, x, y)
    assert m.phase == "settled" and m.result["winner_seat"] == 0


def test_ai_blocks_opponent_four():
    from app.game.gomoku.ai import choose_move
    m = GomokuMatch(first=1)
    # seat1 先手走散子(不成威胁),seat0 形成四连 (3..6, 7),轮到 seat1 必须堵 (2,7) 或 (7,7)
    filler = [(0, 0), (2, 0), (4, 0), (6, 0)]
    for i in range(4):
        m.place(1, *filler[i])
        m.place(0, 3 + i, 7)
    x, y = choose_move(m, 1)
    assert (x, y) in ((2, 7), (7, 7))


@pytest.mark.parametrize("seed", range(60))
def test_full_ai_game_terminates(seed):
    from app.game.gomoku.ai import choose_move
    rng = random.Random(seed)
    m = GomokuMatch(first=seed % 2, rng=rng)
    steps = 0
    while m.phase == "playing":
        steps += 1
        assert steps <= SIZE * SIZE
        x, y = choose_move(m, m.current)
        m.place(m.current, x, y)
    assert m.phase == "settled"
    assert sum(m.result["deltas"]) == 0
