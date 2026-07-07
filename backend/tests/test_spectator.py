"""观战模式端到端:旁观者收到公共快照与事件,但永远看不到任何人的手牌。"""
import os
import tempfile

os.environ.setdefault("MAGIES_FAST", "1")
os.environ.setdefault("MAGIES_DATA", tempfile.mkdtemp(prefix="magies-test-"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _guest(client, nick):
    return client.post("/api/auth/guest", json={"nickname": nick}).json()["token"]


def test_spectator_sees_public_state_only():
    client = TestClient(app)
    ta = _guest(client, "玩家甲")
    tb = _guest(client, "看客乙")
    with client.websocket_connect(f"/ws?token={ta}") as wa, \
            client.websocket_connect(f"/ws?token={tb}") as wb:
        assert wa.receive_json()["t"] == "STATE"
        assert wb.receive_json()["t"] == "STATE"
        wa.send_json({"t": "CREATE", "private": False, "game": "ddz"})
        code = None
        while code is None:
            msg = wa.receive_json()
            if msg["t"] == "STATE" and msg["state"]:
                code = msg["state"]["code"]
        # 乙观战
        wb.send_json({"t": "WATCH", "code": code})
        st = None
        while st is None:
            msg = wb.receive_json()
            if msg["t"] == "STATE" and msg["state"]:
                st = msg["state"]
        assert st["code"] == code and st["my_seat"] is None
        assert st["spectator"] is True
        # 观战者不能操作对局
        wb.send_json({"t": "READY", "ready": True})
        err = wb.receive_json()
        assert err["t"] == "ERROR"
        # 甲开局(AI 补位)打完整局;乙全程收快照+事件,且从无手牌字段
        wa.send_json({"t": "AUTO", "on": True})
        wa.send_json({"t": "READY", "ready": True})
        b_settled = False
        b_states = 0
        for _ in range(30000):
            msg = wb.receive_json()
            if msg["t"] == "STATE" and msg["state"]:
                b_states += 1
                assert "my_hand" not in msg["state"], "观战者不能看到手牌"
                assert msg["state"]["my_seat"] is None
            if msg["t"] == "EVENT" and msg["e"]["e"] in ("settle", "mj_settle"):
                b_settled = True
                break
        assert b_settled and b_states > 5


def test_watch_invalid_code():
    client = TestClient(app)
    tb = _guest(client, "看客丙")
    with client.websocket_connect(f"/ws?token={tb}") as wb:
        assert wb.receive_json()["t"] == "STATE"
        wb.send_json({"t": "WATCH", "code": "000000"})
        assert wb.receive_json()["t"] == "ERROR"


def test_watcher_becomes_player_cleanly():
    client = TestClient(app)
    ta = _guest(client, "玩家丁")
    tb = _guest(client, "看客戊")
    with client.websocket_connect(f"/ws?token={ta}") as wa, \
            client.websocket_connect(f"/ws?token={tb}") as wb:
        wa.receive_json()
        wb.receive_json()
        wa.send_json({"t": "CREATE", "private": False, "game": "ddz"})
        code = None
        while code is None:
            msg = wa.receive_json()
            if msg["t"] == "STATE" and msg["state"]:
                code = msg["state"]["code"]
        wb.send_json({"t": "WATCH", "code": code})
        seen = None
        while seen is None:
            msg = wb.receive_json()
            if msg["t"] == "STATE" and msg["state"] and msg["state"].get("spectator"):
                seen = msg["state"]
        # 从观战转入座:JOIN 后应有座位
        wb.send_json({"t": "JOIN", "code": code})
        seated = None
        while seated is None:
            msg = wb.receive_json()
            if msg["t"] == "STATE" and msg["state"] and msg["state"]["my_seat"] is not None:
                seated = msg["state"]
        assert seated["my_seat"] in (0, 1, 2) and not seated.get("spectator")
