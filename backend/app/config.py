"""运行配置。MAGIES_FAST=1 用于测试:极短计时器让集成测试秒级跑完。"""
import os
import secrets
from pathlib import Path

DATA_DIR = Path(os.environ.get("MAGIES_DATA", Path(__file__).resolve().parents[1] / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "magies.db"

_secret_file = DATA_DIR / "secret.txt"
if os.environ.get("MAGIES_SECRET"):
    SECRET = os.environ["MAGIES_SECRET"]
elif _secret_file.exists():
    SECRET = _secret_file.read_text().strip()
else:
    SECRET = secrets.token_hex(32)
    _secret_file.write_text(SECRET)
    _secret_file.chmod(0o600)

FAST = os.environ.get("MAGIES_FAST") == "1"
ADMIN_KEY = os.environ.get("MAGIES_ADMIN_KEY", "")  # 为空则后台统计接口关闭


def _parse_arcade(raw: str) -> list[dict]:
    """"name=url,name=url" → [{"name":..., "url":...}]。"""
    out = []
    for part in raw.split(","):
        name, _, url = part.strip().partition("=")
        if name and url:
            out.append({"name": name, "url": url})
    return out


# 街机游戏服务探活目标;Docker 部署时用服务名覆盖(见 docker-compose.yml)
ARCADE_SERVICES = _parse_arcade(os.environ.get(
    "MAGIES_ARCADE",
    "bumper-cars=http://127.0.0.1:3001,neon-fps=http://127.0.0.1:3002,"
    "ice-climber=http://127.0.0.1:3003,arena-brawl=http://127.0.0.1:3004,"
    "bomb-party=http://127.0.0.1:3005"))

CALL_TIMEOUT = 0.5 if FAST else 20.0      # 叫分限时
PLAY_TIMEOUT = 0.5 if FAST else 30.0      # 出牌限时
LACK_TIMEOUT = 0.5 if FAST else 12.0      # 麻将定缺限时
CLAIM_TIMEOUT = 0.5 if FAST else 8.0      # 麻将碰杠胡响应限时
FILL_BOTS_AFTER = 0.15 if FAST else 5.0   # 有人准备后多久 AI 补位
BOT_DELAY = (0.01, 0.03) if FAST else (0.9, 1.9)   # 机器人思考时间
AUTO_DELAY = 0.01 if FAST else 0.8        # 托管出牌延迟
SETTLE_IDLE_CLOSE = 60.0                  # 结算后房间空置回收

START_COIN = 10000
COIN_UNIT = 100  # 1 分 = 100 金币
