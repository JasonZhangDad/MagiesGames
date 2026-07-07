"""Magies 3D 棋牌竞技大厅 —— FastAPI 入口:REST + WebSocket。"""
import urllib.request

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import auth, config, db
from .rooms import manager
from .ws import conn_mgr
from .ws import router as ws_router

app = FastAPI(title="Magies 3D 棋牌竞技大厅", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


class GuestIn(BaseModel):
    nickname: str | None = None


class RegisterIn(BaseModel):
    username: str
    password: str
    nickname: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


def _uid_of(authorization: str | None) -> int:
    token = (authorization or "").removeprefix("Bearer ").strip()
    uid = auth.verify_token(token)
    if uid is None or db.get_user(uid) is None:
        raise HTTPException(401, "请先登录")
    return uid


@app.post("/api/auth/guest")
def guest_login(body: GuestIn):
    try:
        return auth.guest_login(body.nickname)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/auth/register")
def register(body: RegisterIn, authorization: str | None = Header(default=None)):
    token = (authorization or "").removeprefix("Bearer ").strip()
    upgrade_uid = auth.verify_token(token) if token else None
    try:
        return auth.register(body.username, body.password, body.nickname, upgrade_uid)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/auth/login")
def login(body: LoginIn):
    try:
        return auth.login(body.username, body.password)
    except PermissionError as e:
        raise HTTPException(401, str(e))


@app.get("/api/me")
def me(authorization: str | None = Header(default=None)):
    return db.get_user(_uid_of(authorization))


@app.get("/api/rooms")
def rooms():
    return {"rooms": manager.list_public()}


@app.get("/api/leaderboard")
def get_leaderboard():
    return {"top": db.leaderboard()}


@app.get("/api/profile/{uid}")
def profile(uid: int):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(404, "用户不存在")
    return {"user": user, "matches": db.recent_matches(uid)}


def _probe(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=0.5) as resp:
            return resp.status < 500
    except Exception:
        return False


@app.get("/api/admin/stats")
def admin_stats(key: str = ""):
    if not config.ADMIN_KEY or key != config.ADMIN_KEY:
        raise HTTPException(403, "无权访问")
    rooms_live = []
    for r in manager.rooms.values():
        rooms_live.append({
            "code": r.code, "game": r.game, "phase": r.phase, "private": r.private,
            "watchers": len(r.spectators),
            "humans": sum(1 for s in r.seats if s and not s.is_bot),
            "bots": sum(1 for s in r.seats if s and s.is_bot),
            "players": [{"nickname": s.nickname, "bot": s.is_bot}
                        for s in r.seats if s],
        })
    return {
        "online": len(conn_mgr.conns),
        "rooms": rooms_live,
        **db.admin_stats(),
        "leaderboard": db.leaderboard(10),
        "recent": db.admin_recent_matches(20),
        "arcade": [{"name": s["name"], "up": _probe(s["url"])}
                   for s in config.ARCADE_SERVICES],
    }


@app.get("/api/health")
def health():
    return {"ok": True, "rooms": len(manager.rooms)}


app.include_router(ws_router)
