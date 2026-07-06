"""SQLite 持久化:账号、钱包、对局、席位、操作日志。单文件零依赖,MVP 足够。"""
import json
import sqlite3
import threading
import time

from .config import DB_PATH, START_COIN

_lock = threading.Lock()
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.execute("PRAGMA journal_mode=WAL")

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_account(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nickname TEXT NOT NULL,
  avatar TEXT NOT NULL DEFAULT '',
  is_guest INTEGER NOT NULL DEFAULT 1,
  created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS user_wallet(
  user_id INTEGER PRIMARY KEY REFERENCES user_account(id),
  coin INTEGER NOT NULL,
  rank_point INTEGER NOT NULL DEFAULT 0,
  wins INTEGER NOT NULL DEFAULT 0,
  losses INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS game_match(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room_code TEXT NOT NULL,
  game_type TEXT NOT NULL DEFAULT 'ddz',
  base INTEGER, multiplier INTEGER, winner_role TEXT,
  spring INTEGER, bombs INTEGER,
  started_at REAL, ended_at REAL
);
CREATE TABLE IF NOT EXISTS game_player(
  match_id INTEGER REFERENCES game_match(id),
  user_id INTEGER,
  nickname TEXT,
  is_bot INTEGER NOT NULL DEFAULT 0,
  seat_no INTEGER, role TEXT,
  delta_coin INTEGER, delta_rank INTEGER, result TEXT
);
CREATE TABLE IF NOT EXISTS game_action_log(
  match_id INTEGER REFERENCES game_match(id),
  seq INTEGER, seat_no INTEGER, action TEXT, payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_player_user ON game_player(user_id);
"""
with _lock:
    _conn.executescript(SCHEMA)
    for ddl in ("ALTER TABLE user_account ADD COLUMN username TEXT",
                "ALTER TABLE user_account ADD COLUMN password_hash TEXT"):
        try:
            _conn.execute(ddl)
        except sqlite3.OperationalError:
            pass  # 列已存在
    _conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_account_username "
                  "ON user_account(username) WHERE username IS NOT NULL")
    _conn.commit()


def _exec(sql, args=()):
    with _lock:
        cur = _conn.execute(sql, args)
        _conn.commit()
        return cur


def create_guest(nickname: str, avatar: str) -> dict:
    cur = _exec("INSERT INTO user_account(nickname, avatar, is_guest, created_at) VALUES(?,?,1,?)",
                (nickname, avatar, time.time()))
    uid = cur.lastrowid
    _exec("INSERT INTO user_wallet(user_id, coin) VALUES(?,?)", (uid, START_COIN))
    return get_user(uid)


def get_user(uid: int) -> dict | None:
    row = _exec("""SELECT a.id, a.nickname, a.avatar, a.username IS NOT NULL AS registered,
                   w.coin, w.rank_point, w.wins, w.losses
                   FROM user_account a JOIN user_wallet w ON w.user_id = a.id
                   WHERE a.id = ?""", (uid,)).fetchone()
    return dict(row) if row else None


def get_credentials(username: str) -> dict | None:
    row = _exec("SELECT id, password_hash FROM user_account WHERE username = ?",
                (username,)).fetchone()
    return dict(row) if row else None


def username_taken(username: str) -> bool:
    return _exec("SELECT 1 FROM user_account WHERE username = ?", (username,)).fetchone() is not None


def attach_credentials(uid: int, username: str, password_hash: str, nickname: str | None):
    _exec("UPDATE user_account SET username = ?, password_hash = ?, is_guest = 0, "
          "nickname = COALESCE(?, nickname) WHERE id = ?",
          (username, password_hash, nickname, uid))


def record_match(room_code: str, started_at: float, result: dict,
                 players: list[dict], history: list[dict]) -> int:
    """players: [{user_id|None, nickname, is_bot, seat_no, role, delta}]"""
    with _lock:
        cur = _conn.execute(
            """INSERT INTO game_match(room_code, base, multiplier, winner_role, spring, bombs,
               started_at, ended_at) VALUES(?,?,?,?,?,?,?,?)""",
            (room_code, result["base"], result["multiplier"], result["winner_role"],
             int(result["spring"]), result["bombs"], started_at, time.time()))
        mid = cur.lastrowid
        for p in players:
            won = (p["role"] == result["winner_role"])
            _conn.execute(
                """INSERT INTO game_player(match_id, user_id, nickname, is_bot, seat_no, role,
                   delta_coin, delta_rank, result) VALUES(?,?,?,?,?,?,?,?,?)""",
                (mid, p["user_id"], p["nickname"], int(p["is_bot"]), p["seat_no"], p["role"],
                 p["delta_coin"], p["delta_rank"], "win" if won else "lose"))
            if p["user_id"] is not None:
                _conn.execute(
                    """UPDATE user_wallet SET
                       coin = MAX(0, coin + ?), rank_point = MAX(0, rank_point + ?),
                       wins = wins + ?, losses = losses + ? WHERE user_id = ?""",
                    (p["delta_coin"], p["delta_rank"], int(won), int(not won), p["user_id"]))
        for seq, h in enumerate(history):
            _conn.execute(
                "INSERT INTO game_action_log(match_id, seq, seat_no, action, payload) VALUES(?,?,?,?,?)",
                (mid, seq, h.get("seat"), h["a"], json.dumps(h, ensure_ascii=False)))
        _conn.commit()
        return mid


def leaderboard(limit=50) -> list[dict]:
    rows = _exec("""SELECT a.id, a.nickname, a.avatar, w.coin, w.rank_point, w.wins, w.losses
                    FROM user_wallet w JOIN user_account a ON a.id = w.user_id
                    WHERE w.wins + w.losses > 0
                    ORDER BY w.rank_point DESC, w.coin DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]


def recent_matches(uid: int, limit=20) -> list[dict]:
    rows = _exec("""SELECT m.id, m.room_code, m.base, m.multiplier, m.winner_role, m.spring,
                    m.bombs, m.ended_at, p.role, p.delta_coin, p.delta_rank, p.result
                    FROM game_player p JOIN game_match m ON m.id = p.match_id
                    WHERE p.user_id = ? ORDER BY m.id DESC LIMIT ?""", (uid, limit)).fetchall()
    return [dict(r) for r in rows]
