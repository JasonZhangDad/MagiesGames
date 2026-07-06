"""账号与鉴权:游客登录、注册(可从游客升级)、登录。token = "<uid>.<hmac_sha256(secret, uid)>"。"""
import hashlib
import hmac
import random
import re
import secrets

from . import db
from .config import SECRET

AVATARS = ["🦊", "🐯", "🐼", "🦁", "🐸", "🐵", "🦄", "🐨", "🐰", "🐲", "🦉", "🐺"]
_NICK_RE = re.compile(r"^[\w一-鿿·—\- ]{1,12}$")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")


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


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"

def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex),
                                n=2 ** 14, r=8, p=1)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def register(username: str, password: str, nickname: str | None,
             upgrade_uid: int | None = None) -> dict:
    username = (username or "").strip()
    if not _USERNAME_RE.match(username):
        raise ValueError("用户名需 3-20 位字母、数字或下划线")
    if len(password or "") < 6:
        raise ValueError("密码至少 6 位")
    nickname = (nickname or "").strip() or None
    if nickname and not _NICK_RE.match(nickname):
        raise ValueError("昵称只支持中英文数字,最长 12 个字符")
    if db.username_taken(username):
        raise ValueError("用户名已被占用")
    pw_hash = _hash_password(password)
    if upgrade_uid is not None:
        user = db.get_user(upgrade_uid)
        if user and not user["registered"]:
            db.attach_credentials(upgrade_uid, username, pw_hash, nickname)
            user = db.get_user(upgrade_uid)
            return {"token": make_token(upgrade_uid), "user": user}
    user = db.create_guest(nickname or f"玩家{random.randint(1000, 9999)}",
                           random.choice(AVATARS))
    db.attach_credentials(user["id"], username, pw_hash, None)
    return {"token": make_token(user["id"]), "user": db.get_user(user["id"])}

def login(username: str, password: str) -> dict:
    cred = db.get_credentials((username or "").strip())
    if not cred or not cred["password_hash"] or not _verify_password(password or "", cred["password_hash"]):
        raise PermissionError("用户名或密码不对")
    return {"token": make_token(cred["id"]), "user": db.get_user(cred["id"])}

def guest_login(nickname: str | None) -> dict:
    nickname = (nickname or "").strip()
    if not nickname:
        nickname = f"玩家{random.randint(1000, 9999)}"
    if not _NICK_RE.match(nickname):
        raise ValueError("昵称只支持中英文数字,最长 12 个字符")
    user = db.create_guest(nickname, random.choice(AVATARS))
    return {"token": make_token(user["id"]), "user": user}
