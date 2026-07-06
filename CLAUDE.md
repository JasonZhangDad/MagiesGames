# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目现状（重要）

本目录是**尚未启动编码的新项目**，当前只有产品规划文档 `Magies-3D-Qipai-Platform-Plan.docx`（2026-07-06，V1.0）。没有代码、没有构建命令、没有测试——骨架搭好后请更新本文件的命令部分。

**Git 注意**：本目录不是独立仓库。git 根在上层 `~/Downloads`（那个仓库跟踪的是 `app/magies-dash`，与本项目无关）。开始写代码前应先在本目录 `git init` 建立独立仓库，避免提交进 Downloads 大仓库。

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
