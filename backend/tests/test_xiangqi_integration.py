"""象棋端到端:游客 → 快速匹配 → AI 补位 → 托管打完 → 结算。"""
import os
import tempfile

os.environ.setdefault("MAGIES_FAST", "1")
os.environ.setdefault("MAGIES_DATA", tempfile.mkdtemp(prefix="magies-test-"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_xiangqi_full_match_via_ws():
    client = TestClient(app)
    token = client.post("/api/auth/guest", json={"nickname": "棋圣"}).json()["token"]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        assert ws.receive_json() == {"t": "STATE", "state": None}
        ws.send_json({"t": "QUICK", "game": "xiangqi"})
        ws.send_json({"t": "AUTO", "on": True})
        ws.send_json({"t": "READY", "ready": True})
        settled = None
        bots = 0
        saw_move = False
        board_ok = False
        for _ in range(60000):
            msg = ws.receive_json()
            if msg["t"] == "STATE" and msg["state"]:
                st = msg["state"]
                assert st["game"] == "xiangqi"
                if st.get("board"):
                    board_ok = len(st["board"]) == 10 and len(st["board"][0]) == 9
            if msg["t"] == "EVENT":
                e = msg["e"]
                if e["e"] == "bot_fill":
                    bots += 1
                elif e["e"] == "xqmove":
                    saw_move = True
                elif e["e"] == "xq_settle":
                    settled = e["result"]
                    break
        assert bots == 1
        assert saw_move and board_ok
        assert settled is not None
        assert sum(settled["deltas"]) == 0
