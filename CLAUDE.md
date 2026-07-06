# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目现状

斗地主 MVP **已上线**:https://games.magies.top（服务器 150.230.47.207,nginx + systemd `magies-games`,代码在 `/opt/magies-games`,静态在 `/var/www/games.magies.top`）。GitHub:https://github.com/JasonZhangDad/MagiesGames。规划文档在 `docs/`。

## 常用命令

```bash
# 后端测试(改规则引擎必跑;含 500 局全 AI 仿真)
cd backend && .venv/bin/python -m pytest tests/ -q
# 单个测试
cd backend && .venv/bin/python -m pytest tests/test_patterns.py::test_plane_pure -q

# 本地起服(前端 5173 已代理 /api /ws 到 8000)
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000 --reload
cd frontend && npm run dev

# 构建与部署(先 build,再上传 dist + 服务器 git pull + 重启服务)
cd frontend && npm run build
ssh -i ~/Downloads/ssh-key-2026-03-27.key ubuntu@150.230.47.207 \
  'cd /opt/magies-games && git pull && sudo systemctl restart magies-games'
```

测试环境变量:`MAGIES_FAST=1`(极短计时器)、`MAGIES_DATA=<dir>`(数据目录)。

## 代码地图

- `backend/app/game/`:斗地主规则引擎纯逻辑(cards/patterns/engine/ai),**不依赖网络与数据库**
- `backend/app/game/mahjong/`:四川血战麻将引擎(tiles/win/engine/ai),同样纯逻辑;Room 按 game_type("ddz" 3 座/"mahjong" 4 座)分支驱动
- `backend/app/rooms.py`:房间编排(AI 补位/回合计时/托管/重连);并发靠单事件循环 + version 版本号,过期任务自动失效
- `backend/app/ws.py`:WS 网关,协议 = 个性化 STATE 快照 + EVENT 事件流;客户端以快照为唯一真相,事件只做动画
- `frontend/src/three/tableScene.js`:3D 对局桌;手牌是公告板(面向相机)且关闭深度测试靠 renderOrder 排序(扇形弧线会让深度关系反转)
- `frontend/src/stores/game.js`:事件必须放队列逐条消费,Vue watcher 合并会吞事件

## 项目定位

Magies 3D 棋牌竞技大厅：基于 three.js 的浏览器 3D 棋牌平台。核心架构是「3D 大厅 + 多游戏插件 + 实时对战服务」，首发只做 **3D 斗地主 MVP**（3 人房、AI 补位、叫/抢地主、出牌、结算），之后按 五子棋 → 象棋 → 麻将 顺序扩展。

**合规红线（不可越过）**：仅虚拟金币/积分/段位。不做现金充值、提现、兑换、抽水、返佣或任何变相兑换。AI 机器人不参与真实奖励排行。

## 规划技术栈

- 前端：Vue3（或 React）+ Vite + three.js，状态用 Pinia/Zustand
- 实时通信：WebSocket / Socket.IO（房间消息、操作广播、心跳）
- 后端：Spring Boot 3 或 NestJS；Redis 存房间状态/匹配队列；PostgreSQL/MySQL 持久化
- 部署：Docker Compose + Nginx/Caddy，MVP 单 VPS 即可

## 核心架构原则

1. **服务端是唯一可信源**。客户端发来的操作只是「意图」，服务端校验合法后才更新状态并广播。three.js 只负责展示/交互/动画，不承载任何规则判断（防改包出牌、偷看手牌）。发牌后客户端只接收自己的手牌与公共信息。

2. **对局由服务端状态机驱动**，阶段只能按合法路径流转：
   `WAITING → DEALING → CALLING → PLAYING → SETTLEMENT → CLOSED`

3. **规则引擎独立于 WebSocket 和数据库**，纯逻辑、可单测。规划的模块拆分：DeckService（洗牌发牌）、CardPatternService（牌型识别/比较）、TurnService（回合与操作权）、LandlordService（叫/抢地主）、MatchStateMachine（阶段推进）、SettlementService（结算积分）、ReplayService（操作序列回放）。每个游戏实现统一接口（初始化、接收操作、校验、推进状态、结算），新游戏只加规则引擎 + 桌面布局 + UI，账号/房间/排行榜/回放/后台全部复用。

4. **规则引擎必须先写单元测试再接前端**。重点覆盖：顺子/飞机/炸弹/王炸识别、带牌数量、出牌比较、回合跳转、托管超时——这些是最容易出线上争议的地方。

5. **动画与真实状态分离**：发牌/出牌动画只是表现层，不能让网络延迟影响规则状态。

## 关键机制（MVP 验收口径）

- AI 机器人补位是核心功能而非装饰：缺人补位、掉线托管、超时代打，保证对局永不卡死
- 断线重连：服务端保存状态快照，60 秒内重连恢复原座位和手牌
- 操作日志（game_action_log 按 seq 记录）同时服务于回放和排查
- 移动端必须可玩：低配模式（简化材质、关阴影、降像素比），牌面用纹理图集减少 draw call
- 完整数据库表设计、REST API 和 WebSocket 消息协议见规划文档第 10、11 节

## 开发路线（8 周排期摘要）

three.js 牌桌原型 → 斗地主规则引擎 → WebSocket 房间通信 → 完整对局闭环 → AI 与重连 → 账号排行 → 运营后台 → 优化上线。原则：不追求游戏多，追求一个游戏足够完整（能稳定运行、能重连、能回放、能统计、能后台管理）再扩展。
