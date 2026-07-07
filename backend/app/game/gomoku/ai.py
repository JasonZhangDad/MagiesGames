"""五子棋 AI:单层筛选 + 前 8 候选二层展开(看对手最佳回应再定)。

评分依据经典模式表:五连 > 活四 > 冲四 > 活三 > 眠三 > 活二。
自己成五直接赢;对手下一手能成五必须堵;
其余局面对头部候选做一步对手推演,避免"贪一手送一手"。
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


def _best_reply(board, who: int) -> int:
    """对方走一手能拿到的最高进攻分(用于二层展开)。"""
    best = 0
    for x, y in _candidates(board):
        a = _line_score(board, x, y, who)
        if a >= 10_000_000:
            return a
        if a > best:
            best = a
    return best


def choose_move(match, seat: int) -> tuple[int, int]:
    board = match.board
    opp = 1 - seat
    scored = []
    must_block, block_at = 0, None
    for x, y in _candidates(board):
        attack = _line_score(board, x, y, seat)
        if attack >= 10_000_000:  # 直接成五
            return x, y
        defend = _line_score(board, x, y, opp)
        if defend >= 10_000_000 and defend > must_block:  # 对手下一手成五,必堵
            must_block, block_at = defend, (x, y)
        scored.append((attack + defend * 0.9, x, y, attack))
    if block_at:
        return block_at
    # 二层展开:前 8 名候选,落子后看对手最佳回应,惩罚"给对手留大招"的选点
    scored.sort(reverse=True)
    best, best_score = None, float("-inf")
    for base, x, y, attack in scored[:8]:
        board[y][x] = seat
        reply = 0 if attack >= 1_000_000 else _best_reply(board, opp)  # 活四已必胜,无需推演
        board[y][x] = -1
        score = base - reply * 0.55 + match.rng.random()  # 微扰打破平手
        if score > best_score:
            best, best_score = (x, y), score
    return best
