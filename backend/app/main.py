"""Magies 3D 棋牌竞技大厅 —— FastAPI 入口:REST + WebSocket。"""
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import auth, db
from .rooms import manager
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


@app.get("/api/health")
def health():
    return {"ok": True, "rooms": len(manager.rooms)}


app.include_router(ws_router)
