"""麻将端到端集成:游客 → 麻将快速匹配 → AI 补满 4 人 → 全托管打完血战 → 结算。"""
import os
import tempfile

os.environ.setdefault("MAGIES_FAST", "1")
os.environ.setdefault("MAGIES_DATA", tempfile.mkdtemp(prefix="magies-test-"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_mahjong_full_match_via_ws():
    client = TestClient(app)
    token = client.post("/api/auth/guest", json={"nickname": "麻友"}).json()["token"]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        assert ws.receive_json() == {"t": "STATE", "state": None}
        ws.send_json({"t": "QUICK", "game": "mahjong"})
        ws.send_json({"t": "AUTO", "on": True})
        ws.send_json({"t": "READY", "ready": True})
        settled = None
        bots = 0
        saw_lack = saw_discard = False
        for _ in range(20000):
            msg = ws.receive_json()
            if msg["t"] == "STATE" and msg["state"]:
                assert msg["state"]["game"] == "mahjong"
            if msg["t"] == "EVENT":
                e = msg["e"]
                if e["e"] == "bot_fill":
                    bots += 1
                elif e["e"] == "lack":
                    saw_lack = True
                elif e["e"] == "discard":
                    saw_discard = True
                elif e["e"] == "mj_settle":
                    settled = e["result"]
                    break
        assert bots == 3
        assert saw_lack and saw_discard
        assert settled is not None
        assert sum(settled["deltas"]) == 0
        assert isinstance(settled["winners"], list)
