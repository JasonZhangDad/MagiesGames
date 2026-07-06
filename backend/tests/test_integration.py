"""端到端集成测试:游客登录 → 快速匹配 → AI 补位 → 全托管打完一整局 → 钱包结算。"""
import os
import tempfile

os.environ.setdefault("MAGIES_FAST", "1")
os.environ.setdefault("MAGIES_DATA", tempfile.mkdtemp(prefix="magies-test-"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_guest_login_and_full_match():
    client = TestClient(app)
    r = client.post("/api/auth/guest", json={"nickname": "测试员"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert r.json()["user"]["coin"] == 10000

    with client.websocket_connect(f"/ws?token={token}") as ws:
        assert ws.receive_json() == {"t": "STATE", "state": None}
        ws.send_json({"t": "QUICK"})
        ws.send_json({"t": "AUTO", "on": True})
        ws.send_json({"t": "READY", "ready": True})
        settled = None
        saw_deal = saw_bots = False
        for _ in range(5000):
            msg = ws.receive_json()
            if msg["t"] == "EVENT":
                e = msg["e"]
                if e["e"] == "bot_fill":
                    saw_bots = True
                if e["e"] == "deal":
                    saw_deal = True
                if e["e"] == "settle":
                    settled = e["result"]
                    break
        assert saw_bots and saw_deal
        assert settled is not None
        assert sum(settled["deltas"]) == 0
        assert settled["winner_role"] in ("landlord", "farmer")

    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["wins"] + me["losses"] == 1
    board = client.get("/api/leaderboard").json()["top"]
    assert any(u["nickname"] == "测试员" for u in board)


def test_bad_token_rejected():
    client = TestClient(app)
    assert client.get("/api/me", headers={"Authorization": "Bearer 1.deadbeef"}).status_code == 401


def test_join_missing_room_gives_error():
    client = TestClient(app)
    token = client.post("/api/auth/guest", json={}).json()["token"]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.receive_json()
        ws.send_json({"t": "JOIN", "code": "000000"})
        for _ in range(10):
            msg = ws.receive_json()
            if msg["t"] == "ERROR":
                assert "房间" in msg["msg"]
                return
        raise AssertionError("未收到错误提示")
