"""游客登录与 HMAC token。token = "<uid>.<hmac_sha256(secret, uid)>"。"""
import hashlib
import hmac
import random
import re

from . import db
from .config import SECRET

AVATARS = ["🦊", "🐯", "🐼", "🦁", "🐸", "🐵", "🦄", "🐨", "🐰", "🐲", "🦉", "🐺"]
_NICK_RE = re.compile(r"^[\w一-鿿·—\- ]{1,12}$")


def _sign(uid: int) -> str:
    return hmac.new(SECRET.encode(), str(uid).encode(), hashlib.sha256).hexdigest()[:32]


def make_token(uid: int) -> str:
    return f"{uid}.{_sign(uid)}"


def verify_token(token: str | None) -> int | None:
    if not token or "." not in token:
        return None
    uid_s, sig = token.split(".", 1)
    if not uid_s.isdigit():
        return None
    uid = int(uid_s)
    return uid if hmac.compare_digest(sig, _sign(uid)) else None


def guest_login(nickname: str | None) -> dict:
    nickname = (nickname or "").strip()
    if not nickname:
        nickname = f"玩家{random.randint(1000, 9999)}"
    if not _NICK_RE.match(nickname):
        raise ValueError("昵称只支持中英文数字,最长 12 个字符")
    user = db.create_guest(nickname, random.choice(AVATARS))
    return {"token": make_token(user["id"]), "user": user}
