"""运营后台统计接口:密钥保护 + 指标字段。"""
import os
import tempfile

os.environ.setdefault("MAGIES_FAST", "1")
os.environ.setdefault("MAGIES_DATA", tempfile.mkdtemp(prefix="magies-test-"))
os.environ.setdefault("MAGIES_ADMIN_KEY", "test-admin-key")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_admin_requires_key():
    client = TestClient(app)
    assert client.get("/api/admin/stats").status_code == 403
    assert client.get("/api/admin/stats?key=wrong").status_code == 403


def test_admin_stats_fields_and_counts():
    client = TestClient(app)
    client.post("/api/auth/guest", json={"nickname": "统计君"})
    r = client.get("/api/admin/stats?key=test-admin-key")
    assert r.status_code == 200
    data = r.json()
    for k in ("online", "rooms", "users_total", "users_registered",
              "matches_total", "matches_today", "matches_by_game",
              "leaderboard", "recent"):
        assert k in data, f"缺字段 {k}"
    assert data["users_total"] >= 1
    assert isinstance(data["rooms"], list)
    assert isinstance(data["matches_by_game"], dict)


def test_admin_counts_matches_after_game():
    client = TestClient(app)
    token = client.post("/api/auth/guest", json={"nickname": "对局君"}).json()["token"]
    before = client.get("/api/admin/stats?key=test-admin-key").json()["matches_total"]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        ws.receive_json()
        ws.send_json({"t": "QUICK", "game": "ddz"})
        ws.send_json({"t": "AUTO", "on": True})
        ws.send_json({"t": "READY", "ready": True})
        for _ in range(20000):
            msg = ws.receive_json()
            if msg["t"] == "EVENT" and msg["e"]["e"] == "settle":
                break
    after = client.get("/api/admin/stats?key=test-admin-key").json()
    assert after["matches_total"] == before + 1
    assert after["matches_today"] >= 1
    assert after["matches_by_game"].get("ddz", 0) >= 1
