"""五子棋 AI:单层局面评估——对每个候选点评"进攻分+防守分",取最高。

评分依据经典模式表:五连 > 活四 > 冲四 > 活三 > 眠三 > 活二。
自己成五直接赢;对手下一手能成五必须堵。强度定位:陪练级,快而不卡局。
"""
from .engine import DIRS, SIZE

# (连子数, 开放端数) → 分值
SCORE = {
    (5, 0): 10_000_000, (5, 1): 10_000_000, (5, 2): 10_000_000,
    (4, 2): 1_000_000, (4, 1): 100_000,
    (3, 2): 50_000, (3, 1): 5_000,
    (2, 2): 1_000, (2, 1): 100,
    (1, 2): 20, (1, 1): 5,
}


def _line_score(board, x: int, y: int, who: int) -> int:
    """假设 who 落在 (x,y),四个方向的模式分之和。"""
    total = 0
    for dx, dy in DIRS:
        count = 1
        open_ends = 0
        for sgn in (1, -1):
            nx, ny = x + dx * sgn, y + dy * sgn
            while 0 <= nx < SIZE and 0 <= ny < SIZE and board[ny][nx] == who:
                count += 1
                nx += dx * sgn
                ny += dy * sgn
            if 0 <= nx < SIZE and 0 <= ny < SIZE and board[ny][nx] == -1:
                open_ends += 1
        total += SCORE.get((min(count, 5), open_ends), SCORE[(5, 0)] if count > 5 else 0)
    return total


def _candidates(board) -> list[tuple[int, int]]:
    """只考虑已有棋子附近 2 格内的空点;空盘走天元。"""
    stones = [(x, y) for y in range(SIZE) for x in range(SIZE) if board[y][x] != -1]
    if not stones:
        return [(SIZE // 2, SIZE // 2)]
    cand = set()
    for x, y in stones:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = x + dx, y + dy
                if 0 <= nx < SIZE and 0 <= ny < SIZE and board[ny][nx] == -1:
                    cand.add((nx, ny))
    return list(cand)


def choose_move(match, seat: int) -> tuple[int, int]:
    board = match.board
    opp = 1 - seat
    best, best_score = None, -1
    for x, y in _candidates(board):
        attack = _line_score(board, x, y, seat)
        defend = _line_score(board, x, y, opp)
        if attack >= 10_000_000:  # 直接成五
            return x, y
        score = attack + defend * 0.9 + match.rng.random()  # 微扰打破平手
        if score > best_score:
            best, best_score = (x, y), score
    return best
