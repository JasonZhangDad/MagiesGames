"""中国象棋状态机:完整走子规则/将军/绝杀/困毙/60回合无吃子判和。纯逻辑无 IO。

坐标 x∈[0,8] y∈[0,9],红方在下(y0 红底线),红先行。
side: 0 红 / 1 黑;board[y][x] = None 或 (side, kind)。
kind: k帅将 a士 b相象 n马 r车 c炮 p兵卒。
无合法着法即负(含绝杀与困毙);计分:胜 +2 / 负 -2 / 和 0。
"""
import random

W, H = 9, 10
NO_CAPTURE_DRAW = 120  # 半回合数(60 整回合)无吃子判和

KIND_LABEL = {
    ("r", 0): {"k": "帅", "a": "仕", "b": "相", "n": "马", "r": "车", "c": "炮", "p": "兵"},
    ("r", 1): {"k": "将", "a": "士", "b": "象", "n": "马", "r": "车", "c": "炮", "p": "卒"},
}


def label_of(side: int, kind: str) -> str:
    return KIND_LABEL[("r", side)][kind]


def initial_board():
    board = [[None] * W for _ in range(H)]
    back = ["r", "n", "b", "a", "k", "a", "b", "n", "r"]
    for x, kind in enumerate(back):
        board[0][x] = (0, kind)
        board[9][x] = (1, kind)
    for x in (1, 7):
        board[2][x] = (0, "c")
        board[7][x] = (1, "c")
    for x in range(0, 9, 2):
        board[3][x] = (0, "p")
        board[6][x] = (1, "p")
    return board


def in_palace(side: int, x: int, y: int) -> bool:
    if not 3 <= x <= 5:
        return False
    return 0 <= y <= 2 if side == 0 else 7 <= y <= 9


def own_half(side: int, y: int) -> bool:
    return y <= 4 if side == 0 else y >= 5


class XiangqiMatch:
    SEATS = 2

    def __init__(self, red_seat: int = 0, board=None, turn_side: int = 0,
                 rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.red_seat = red_seat
        self.board = board if board is not None else initial_board()
        self.turn_side = turn_side  # 0 红 1 黑
        self.phase = "playing"
        self.halfmove_clock = 0
        self.moves: list[dict] = []
        self.history = self.moves
        self.last: dict | None = None
        self.result: dict | None = None

    # ---------- 座位与阵营 ----------

    def side_of(self, seat: int) -> int:
        return 0 if seat == self.red_seat else 1

    def seat_of_side(self, side: int) -> int:
        return self.red_seat if side == 0 else 1 - self.red_seat

    @property
    def current(self) -> int | None:
        return self.seat_of_side(self.turn_side) if self.phase == "playing" else None

    # ---------- 走法生成 ----------

    def king_pos(self, side: int) -> tuple[int, int] | None:
        for y in (range(0, 3) if side == 0 else range(7, 10)):  # 王不出九宫
            for x in range(3, 6):
                if self.board[y][x] == (side, "k"):
                    return x, y
        return None

    def pseudo_moves(self, x: int, y: int) -> list[tuple[int, int]]:
        piece = self.board[y][x]
        if piece is None:
            return []
        side, kind = piece
        b = self.board
        out = []

        def ok(nx, ny):
            return 0 <= nx < W and 0 <= ny < H and (b[ny][nx] is None or b[ny][nx][0] != side)

        if kind == "r" or kind == "c":
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                while 0 <= nx < W and 0 <= ny < H and b[ny][nx] is None:
                    out.append((nx, ny))
                    nx += dx
                    ny += dy
                if kind == "r":
                    if 0 <= nx < W and 0 <= ny < H and b[ny][nx][0] != side:
                        out.append((nx, ny))
                else:  # 炮:跳一个架吃子
                    nx += dx
                    ny += dy
                    while 0 <= nx < W and 0 <= ny < H:
                        if b[ny][nx] is not None:
                            if b[ny][nx][0] != side:
                                out.append((nx, ny))
                            break
                        nx += dx
                        ny += dy
        elif kind == "n":
            for dx, dy, lx, ly in ((2, 1, 1, 0), (2, -1, 1, 0), (-2, 1, -1, 0), (-2, -1, -1, 0),
                                   (1, 2, 0, 1), (-1, 2, 0, 1), (1, -2, 0, -1), (-1, -2, 0, -1)):
                if 0 <= x + lx < W and 0 <= y + ly < H and b[y + ly][x + lx] is None \
                        and ok(x + dx, y + dy):
                    out.append((x + dx, y + dy))
        elif kind == "b":
            for dx, dy in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
                nx, ny = x + dx, y + dy
                ex, ey = x + dx // 2, y + dy // 2
                if ok(nx, ny) and own_half(side, ny) and b[ey][ex] is None:
                    out.append((nx, ny))
        elif kind == "a":
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = x + dx, y + dy
                if ok(nx, ny) and in_palace(side, nx, ny):
                    out.append((nx, ny))
        elif kind == "k":
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if ok(nx, ny) and in_palace(side, nx, ny):
                    out.append((nx, ny))
        elif kind == "p":
            fwd = 1 if side == 0 else -1
            if ok(x, y + fwd):
                out.append((x, y + fwd))
            if not own_half(side, y):  # 过河后可横走
                for dx in (1, -1):
                    if ok(x + dx, y):
                        out.append((x + dx, y))
        return out

    def in_check(self, side: int) -> bool:
        """从王的位置反向探测:车/炮/对脸沿射线,马看反向马腿,兵看邻格。"""
        kp = self.king_pos(side)
        if kp is None:
            return True
        kx, ky = kp
        enemy = 1 - side
        b = self.board
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cnt = 0
            nx, ny = kx + dx, ky + dy
            while 0 <= nx < W and 0 <= ny < H:
                p = b[ny][nx]
                if p is not None:
                    cnt += 1
                    if cnt == 1:
                        if p[0] == enemy and p[1] in ("r", "k"):  # 车杀 / 对脸
                            return True
                    else:
                        if p[0] == enemy and p[1] == "c":  # 炮隔一子
                            return True
                        break
                nx += dx
                ny += dy
        for dx, dy in ((2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)):
            mx, my = kx + dx, ky + dy
            if not (0 <= mx < W and 0 <= my < H) or b[my][mx] != (enemy, "n"):
                continue
            lx = mx - dx // 2 if abs(dx) == 2 else mx
            ly = my - dy // 2 if abs(dy) == 2 else my
            if b[ly][lx] is None:  # 马腿无子,真将军
                return True
        fwd = -1 if enemy == 1 else 1  # 敌兵的前进方向(指向本方王)
        if 0 <= ky - fwd < H and b[ky - fwd][kx] == (enemy, "p"):
            return True
        for dx in (1, -1):
            if 0 <= kx + dx < W and b[ky][kx + dx] == (enemy, "p") \
                    and not own_half(enemy, ky):
                return True
        return False

    def _simulate_ok(self, frm, to) -> bool:
        """走完后自己不被将军且不对脸。"""
        (fx, fy), (tx, ty) = frm, to
        piece = self.board[fy][fx]
        captured = self.board[ty][tx]
        self.board[ty][tx] = piece
        self.board[fy][fx] = None
        bad = self.in_check(piece[0])
        self.board[fy][fx] = piece
        self.board[ty][tx] = captured
        return not bad

    def legal_moves(self, side: int) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        out = []
        for y in range(H):
            for x in range(W):
                p = self.board[y][x]
                if p and p[0] == side:
                    for to in self.pseudo_moves(x, y):
                        if self._simulate_ok((x, y), to):
                            out.append(((x, y), to))
        return out

    # ---------- 行棋 ----------

    def _require(self, cond: bool, msg: str):
        if not cond:
            raise ValueError(msg)

    def move(self, seat: int, frm: tuple[int, int], to: tuple[int, int]):
        self._require(self.phase == "playing", "对局已结束")
        self._require(seat == self.current, "还没轮到你")
        fx, fy = frm
        tx, ty = to
        self._require(0 <= fx < W and 0 <= fy < H and 0 <= tx < W and 0 <= ty < H, "越界")
        piece = self.board[fy][fx]
        side = self.side_of(seat)
        self._require(piece is not None and piece[0] == side, "这里没有你的棋子")
        self._require((tx, ty) in self.pseudo_moves(fx, fy), "不符合走子规则")
        self._require(self._simulate_ok(frm, to), "走后被将军/对脸,不能这么走")
        captured = self.board[ty][tx]
        self.board[ty][tx] = piece
        self.board[fy][fx] = None
        self.halfmove_clock = 0 if captured else self.halfmove_clock + 1
        rec = {"a": "move", "seat": seat, "from": [fx, fy], "to": [tx, ty],
               "kind": piece[1], "captured": captured[1] if captured else None}
        self.moves.append(rec)
        self.last = rec
        enemy = 1 - side
        if not self.legal_moves(enemy):  # 绝杀或困毙
            self._finish(winner_side=side)
        elif self.halfmove_clock >= NO_CAPTURE_DRAW:
            self._finish(winner_side=None)
        else:
            self.turn_side = enemy

    def _finish(self, winner_side: int | None):
        self.phase = "settled"
        if winner_side is None:
            deltas = [0, 0]
            winner_seat = None
        else:
            winner_seat = self.seat_of_side(winner_side)
            deltas = [2, -2] if winner_seat == 0 else [-2, 2]
        self.result = {"winner_seat": winner_seat, "deltas": deltas,
                       "moves": len(self.moves)}
