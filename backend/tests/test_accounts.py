"""注册/登录/游客升级测试。"""
import os
import tempfile

os.environ.setdefault("MAGIES_FAST", "1")
os.environ.setdefault("MAGIES_DATA", tempfile.mkdtemp(prefix="magies-test-"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_register_and_login():
    r = client.post("/api/auth/register",
                    json={"username": "player_one", "password": "secret66", "nickname": "壹号玩家"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["nickname"] == "壹号玩家"
    assert data["user"]["coin"] == 10000
    assert "password" not in str(data["user"])

    r = client.post("/api/auth/login", json={"username": "player_one", "password": "secret66"})
    assert r.status_code == 200
    assert r.json()["user"]["id"] == data["user"]["id"]


def test_login_wrong_password():
    client.post("/api/auth/register", json={"username": "p2", "password": "abcdef"})
    r = client.post("/api/auth/login", json={"username": "p2", "password": "wrong!"})
    assert r.status_code == 401


def test_register_duplicate_username():
    client.post("/api/auth/register", json={"username": "dup_name", "password": "abcdef"})
    r = client.post("/api/auth/register", json={"username": "dup_name", "password": "abcdef"})
    assert r.status_code == 400


def test_register_validation():
    assert client.post("/api/auth/register",
                       json={"username": "ab", "password": "abcdef"}).status_code == 400
    assert client.post("/api/auth/register",
                       json={"username": "okname", "password": "123"}).status_code == 400


def test_guest_upgrade_keeps_wallet():
    guest = client.post("/api/auth/guest", json={"nickname": "过客"}).json()
    token = guest["token"]
    r = client.post("/api/auth/register",
                    json={"username": "upgraded", "password": "abcdef"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["user"]["id"] == guest["user"]["id"]  # 同一账号,金币战绩保留
    r = client.post("/api/auth/login", json={"username": "upgraded", "password": "abcdef"})
    assert r.json()["user"]["id"] == guest["user"]["id"]


def test_guest_login_still_works():
    r = client.post("/api/auth/guest", json={})
    assert r.status_code == 200
