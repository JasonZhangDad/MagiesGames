# Magies 3D 棋牌竞技大厅

浏览器里的 3D 斗地主竞技平台:three.js 沉浸牌桌 + 服务端权威规则引擎 + AI 补位 + 断线重连。
**线上地址:https://games.magies.top** · 仅虚拟积分,纯娱乐,不涉及任何现金交易。

## 功能

- 🃏 **3D 斗地主完整闭环**:游客秒进 → 匹配/建房/私密房 → 叫分抢地主 → 出牌(提示/托管)→ 结算(炸弹翻倍/春天)
- 🀄 **四川血战麻将**:108 张万筒条、定缺(缺一门)、碰/明暗补杠、血战到底(胡牌离场继续打、一炮多响)、番型结算(七对/龙七对/碰碰胡/清一色/杠上开花)
- 🤖 **AI 机器人**:缺人秒补位、掉线代打、超时托管,对局永不卡死
- 👥 **多人实时对战**:WebSocket 快照+事件协议,断线 60 秒内重连恢复原局
- 🏆 **账号体系**:游客一键进、注册/登录、游客无损升级、排行榜、战绩、操作日志回放数据
- 📱 **多端自适应 + PWA**:手机/平板/桌面,可安装到主屏,低配模式
- 🛡️ **服务端唯一可信源**:客户端只发"意图",所有规则校验在服务端,防改包/偷看手牌

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + three.js + Pinia + GSAP(扑克纹理 Canvas 程序化生成,零美术资源) |
| 后端 | FastAPI + WebSocket(asyncio 单事件循环 + version 版本号并发控制) |
| 规则引擎 | 纯 Python 模块,独立于网络与存储,571 项测试(含 500 局全 AI 仿真) |
| 存储 | SQLite(账号/钱包/对局/席位/操作日志) |
| 部署 | nginx(静态+反代+WS)+ systemd + Cloudflare |

## 本地开发

```bash
# 后端(Python 3.12+)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# 前端(Node 20+)
cd frontend
npm install
npm run dev        # http://localhost:5173,已配置 /api /ws 代理

# 测试
cd backend && .venv/bin/python -m pytest tests/ -q
```

## 部署(生产)

前端 `npm run build` 后把 `dist/` 放到静态目录;后端 `uvicorn app.main:app --host 127.0.0.1 --port 8102` 由 systemd 托管;nginx 配置见 `/etc/nginx/sites-available/games.magies.top`(静态 + `/api` 反代 + `/ws` 升级头)。数据目录由 `MAGIES_DATA` 环境变量指定。

## 目录结构

```
backend/app/game/    规则引擎:cards 牌堆 / patterns 牌型 / engine 状态机 / ai 机器人
backend/app/         rooms 房间编排 / ws 网关 / auth 账号 / db 持久化 / main 入口
backend/tests/       571 项测试(牌型全覆盖 + 状态机 + AI 仿真 + 集成)
frontend/src/three/  cardTexture 纹理 / tableScene 对局桌 / landingScene 落地页
frontend/src/views/  Landing / Lobby / GameView
docs/                产品规划文档
```

## 路线图

斗地主(已上线)→ 血战麻将(已上线)→ 五子棋 → 中国象棋。新游戏只需新增规则引擎 + 桌面布局 + UI,账号/房间/排行/回放全部复用。
