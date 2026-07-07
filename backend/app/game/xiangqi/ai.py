"""象棋 AI:合法着法 + 一步半评估——吃子收益 - 走后被吃的最大损失 + 进军小奖励。

强度定位:陪练级。绝杀机会(走后对方无合法着法)直接选取。
"""
from .engine import H, W, own_half

VAL = {"k": 100000, "r": 900, "n": 420, "c": 460, "b": 210, "a": 210, "p": 110}


def _apply(m, frm, to):
    (fx, fy), (tx, ty) = frm, to
    piece = m.board[fy][fx]
    cap = m.board[ty][tx]
    m.board[ty][tx] = piece
    m.board[fy][fx] = None
    return piece, cap


def _undo(m, frm, to, piece, cap):
    (fx, fy), (tx, ty) = frm, to
    m.board[fy][fx] = piece
    m.board[ty][tx] = cap


def _defended(m, side: int, ax: int, ay: int, tx: int, ty: int) -> bool:
    """模拟敌子 (ax,ay) 吃到 (tx,ty) 后,我方能否回吃。"""
    attacker = m.board[ay][ax]
    victim = m.board[ty][tx]
    m.board[ty][tx] = attacker
    m.board[ay][ax] = None
    hit = False
    for y in range(H):
        for x in range(W):
            p = m.board[y][x]
            if p and p[0] == side and (tx, ty) in m.pseudo_moves(x, y):
                hit = True
                break
        if hit:
            break
    m.board[ay][ax] = attacker
    m.board[ty][tx] = victim
    return hit


def _max_enemy_capture(m, side: int) -> int:
    """走完后敌方最优吃子的净收益(悬子惩罚)。
    有保护的子按兑子净值算:吃了我 110 的兵要赔 900 的车就不算威胁。"""
    enemy = 1 - side
    worst = 0
    for y in range(H):
        for x in range(W):
            p = m.board[y][x]
            if p and p[0] == enemy:
                for tx, ty in m.pseudo_moves(x, y):
                    t = m.board[ty][tx]
                    if t and t[0] == side:
                        net = VAL[t[1]]
                        if net > worst and _defended(m, side, x, y, tx, ty):
                            net -= int(VAL[p[1]] * 0.9)
                        if net > worst:
                            worst = net
    return worst


def choose_move(match, seat: int):
    side = match.side_of(seat)
    moves = match.legal_moves(side)
    if not moves:
        return None
    best, best_sc = None, float("-inf")
    for frm, to in moves:
        piece, cap = _apply(match, frm, to)
        gain = VAL[cap[1]] if cap else 0
        if match.in_check(1 - side) and not match.legal_moves(1 - side):  # 绝杀
            _undo(match, frm, to, piece, cap)
            return frm, to
        risk = _max_enemy_capture(match, side)
        advance = 0
        if piece[1] == "p" and not own_half(side, to[1]):
            advance = 30  # 兵过河
        elif piece[1] in ("r", "n", "c"):
            advance = 6 - abs(to[0] - 4)  # 靠中一点点好
        if match.in_check(1 - side):
            advance += 24  # 将军施压
        sc = gain - risk * 0.9 + advance + match.rng.random()
        _undo(match, frm, to, piece, cap)
        if sc > best_sc:
            best, best_sc = (frm, to), sc
    return best
