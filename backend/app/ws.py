"""WebSocket 网关:每用户一条连接 + 出站队列,消息按序推送。"""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import db
from .auth import verify_token
from .rooms import manager

log = logging.getLogger("magies.ws")
router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.conns: dict[int, tuple[WebSocket, asyncio.Queue, asyncio.Task]] = {}

    def attach(self, uid: int, ws: WebSocket):
        old = self.conns.pop(uid, None)
        if old:
            old[2].cancel()
            asyncio.get_running_loop().create_task(self._close_quiet(old[0]))
        q: asyncio.Queue = asyncio.Queue()
        task = asyncio.get_running_loop().create_task(self._sender(ws, q))
        self.conns[uid] = (ws, q, task)

    async def _close_quiet(self, ws: WebSocket):
        try:
            await ws.close(code=4000)
        except Exception:
            pass

    async def _sender(self, ws: WebSocket, q: asyncio.Queue):
        try:
            while True:
                await ws.send_json(await q.get())
        except Exception:
            pass

    def detach(self, uid: int, ws: WebSocket) -> bool:
        cur = self.conns.get(uid)
        if cur and cur[0] is ws:
            cur[2].cancel()
            self.conns.pop(uid, None)
            return True
        return False

    def send(self, uid: int, msg: dict):
        cur = self.conns.get(uid)
        if cur:
            cur[1].put_nowait(msg)


conn_mgr = ConnectionManager()
manager.send_fn = conn_mgr.send


def _handle(uid: int, msg: dict):
    t = msg.get("t")
    if t == "PING":
        conn_mgr.send(uid, {"t": "PONG"})
        return
    room = manager.room_of(uid)
    if t in ("QUICK", "CREATE", "JOIN"):
        user = db.get_user(uid)
        if not user:
            raise ValueError("账号不存在")
        if t == "QUICK":
            manager.quick_match(user)
        elif t == "CREATE":
            manager.create(user, private=bool(msg.get("private")))
        else:
            code = str(msg.get("code", "")).strip()
            manager.join_code(user, code)
        return
    if t == "LEAVE":
        manager.leave(uid)
        conn_mgr.send(uid, {"t": "STATE", "state": None})
        return
    if room is None:
        raise ValueError("你还没有加入房间")
    seat = room.seat_of(uid)
    if t == "READY":
        room.set_ready(uid, bool(msg.get("ready", True)))
    elif t == "CALL":
        room.do_call(seat, int(msg.get("score", 0)))
    elif t == "PLAY":
        cards = msg.get("cards")
        if not isinstance(cards, list) or not all(isinstance(c, int) for c in cards) \
                or not (1 <= len(cards) <= 20):
            raise ValueError("出牌数据不合法")
        room.do_play(seat, cards)
    elif t == "PASS":
        room.do_pass(seat)
    elif t == "HINT":
        conn_mgr.send(uid, {"t": "HINT", "cards": room.hint_for(uid)})
    elif t == "AUTO":
        room.set_auto(uid, bool(msg.get("on")))
    elif t == "CHAT":
        room.chat(uid, str(msg.get("text", "")))


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    uid = verify_token(ws.query_params.get("token"))
    user = db.get_user(uid) if uid else None
    if not user:
        await ws.close(code=4401)
        return
    await ws.accept()
    conn_mgr.attach(uid, ws)
    room = manager.room_of(uid)
    if room:
        room.on_reconnect(uid)
    else:
        conn_mgr.send(uid, {"t": "STATE", "state": None})
    try:
        while True:
            try:
                msg = await ws.receive_json()
            except (ValueError, TypeError):
                continue  # 非 JSON 消息忽略
            if not isinstance(msg, dict):
                continue
            try:
                _handle(uid, msg)
            except ValueError as e:
                conn_mgr.send(uid, {"t": "ERROR", "msg": str(e)})
            except Exception:
                log.exception("ws 消息处理异常 uid=%s msg=%s", uid, msg)
                conn_mgr.send(uid, {"t": "ERROR", "msg": "服务器开小差了,请重试"})
    except WebSocketDisconnect:
        pass
    finally:
        if conn_mgr.detach(uid, ws):
            room = manager.room_of(uid)
            if room:
                room.on_disconnect(uid)
