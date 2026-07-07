"""五子棋端到端:游客 → 快速匹配 → AI 补位 → 托管打完 → 结算。"""
import os
import tempfile

os.environ.setdefault("MAGIES_FAST", "1")
os.environ.setdefault("MAGIES_DATA", tempfile.mkdtemp(prefix="magies-test-"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_gomoku_full_match_via_ws():
    client = TestClient(app)
    token = client.post("/api/auth/guest", json={"nickname": "棋士"}).json()["token"]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        assert ws.receive_json() == {"t": "STATE", "state": None}
        ws.send_json({"t": "QUICK", "game": "gomoku"})
        ws.send_json({"t": "AUTO", "on": True})
        ws.send_json({"t": "READY", "ready": True})
        settled = None
        bots = 0
        saw_place = False
        board_ok = False
        for _ in range(20000):
            msg = ws.receive_json()
            if msg["t"] == "STATE" and msg["state"]:
                st = msg["state"]
                assert st["game"] == "gomoku"
                if st.get("board"):
                    board_ok = len(st["board"]) == 15 and len(st["board"][0]) == 15
            if msg["t"] == "EVENT":
                e = msg["e"]
                if e["e"] == "bot_fill":
                    bots += 1
                elif e["e"] == "place":
                    saw_place = True
                elif e["e"] == "gmk_settle":
                    settled = e["result"]
                    break
        assert bots == 1
        assert saw_place and board_ok
        assert settled is not None
        assert sum(settled["deltas"]) == 0
        assert sum(settled["coin_deltas"]) == 0


def test_gomoku_place_validation_via_ws():
    client = TestClient(app)
    token = client.post("/api/auth/guest", json={"nickname": "手滑君"}).json()["token"]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.receive_json()
        ws.send_json({"t": "PLACE", "x": 7, "y": 7})
        assert ws.receive_json()["t"] == "ERROR"  # 没进房间
        ws.send_json({"t": "QUICK", "game": "ddz"})
        ws.send_json({"t": "PLACE", "x": 7, "y": 7})
        err = None
        for _ in range(50):
            msg = ws.receive_json()
            if msg["t"] == "ERROR":
                err = msg
                break
        assert err is not None  # 斗地主房里不能落子
