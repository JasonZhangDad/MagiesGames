"""五子棋状态机:15 路无禁手,连五(及以上)即胜,满盘平局。纯逻辑无 IO。

board[y][x] = -1 空 / 0 seat0 / 1 seat1;first 座位执黑先行。
计分:胜者 +2 单位,负者 -2;平局各 0。
"""
import random

SIZE = 15
DIRS = ((1, 0), (0, 1), (1, 1), (1, -1))


class GomokuMatch:
    SEATS = 2

    def __init__(self, first: int = 0, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.first = first
        self.board = [[-1] * SIZE for _ in range(SIZE)]
        self.phase = "playing"
        self.current: int | None = first
        self.moves: list[dict] = []  # {"seat","x","y"}
        self.last: tuple[int, int] | None = None
        self.result: dict | None = None
        self.history = self.moves  # 与其他引擎统一的操作日志别名

    def _require(self, cond: bool, msg: str):
        if not cond:
            raise ValueError(msg)

    def place(self, seat: int, x: int, y: int):
        self._require(self.phase == "playing", "对局已结束")
        self._require(seat == self.current, "还没轮到你")
        self._require(0 <= x < SIZE and 0 <= y < SIZE, "落子越界")
        self._require(self.board[y][x] == -1, "这里已经有子了")
        self.board[y][x] = seat
        self.moves.append({"a": "place", "seat": seat, "x": x, "y": y})
        self.last = (x, y)
        line = self.win_line(x, y)
        if line:
            self._finish(winner=seat, line=line)
        elif len(self.moves) >= SIZE * SIZE:
            self._finish(winner=None, line=None)
        else:
            self.current = 1 - seat

    def win_line(self, x: int, y: int) -> list[tuple[int, int]] | None:
        """以 (x,y) 为最后落子,返回构成的 ≥5 连线坐标(无禁手,长连也算胜)。"""
        who = self.board[y][x]
        for dx, dy in DIRS:
            cells = [(x, y)]
            for sgn in (1, -1):
                nx, ny = x + dx * sgn, y + dy * sgn
                while 0 <= nx < SIZE and 0 <= ny < SIZE and self.board[ny][nx] == who:
                    cells.append((nx, ny))
                    nx += dx * sgn
                    ny += dy * sgn
            if len(cells) >= 5:
                return sorted(cells)
        return None

    def _finish(self, winner: int | None, line):
        self.phase = "settled"
        self.current = None
        if winner is None:
            deltas = [0, 0]
        else:
            deltas = [2, -2] if winner == 0 else [-2, 2]
        self.result = {"winner_seat": winner, "deltas": deltas,
                       "win_line": line, "moves": len(self.moves)}
