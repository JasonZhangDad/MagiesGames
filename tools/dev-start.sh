#!/bin/bash
# MagiesGames 本地开发快速启动脚本
# 用法：bash tools/dev-start.sh [游戏slug...]
# 示例：bash tools/dev-start.sh bumper-cars neon-fps （只启动指定游戏）
# 示例：bash tools/dev-start.sh all                  （启动全部游戏）

set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
GAMES_DIR="$REPO/tools/games-system-import/games"

declare -A GAME_DIR_MAP=(
  [bumper-cars]="crazy-bumper-cars"
  [neon-fps]="neon-arena-fps"
  [ice-climber]="ice-climber-arena"
  [arena-brawl]="arena-brawl"
  [bomb-party]="bomb-party"
)
declare -A GAME_PORT_MAP=(
  [bumper-cars]=3001
  [neon-fps]=3002
  [ice-climber]=3003
  [arena-brawl]=3004
  [bomb-party]=3005
)

# 选择要启动的游戏
if [[ "$1" == "all" || $# -eq 0 ]]; then
  SELECTED=("bumper-cars" "neon-fps" "ice-climber" "arena-brawl" "bomb-party")
else
  SELECTED=("$@")
fi

echo "🎮 MagiesGames 开发启动"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 启动各游戏服务
for slug in "${SELECTED[@]}"; do
  dir="${GAME_DIR_MAP[$slug]}"
  port="${GAME_PORT_MAP[$slug]}"
  game_path="$GAMES_DIR/$dir"

  if [[ ! -d "$game_path" ]]; then
    echo "⚠️  找不到游戏目录：$game_path，跳过"
    continue
  fi

  # 安装依赖
  if [[ ! -d "$game_path/node_modules" ]]; then
    echo "📦 安装 $slug 依赖..."
    (cd "$game_path" && npm install --silent)
  fi

  echo "🚀 启动 $slug → http://localhost:$port"
  PORT=$port (cd "$game_path" && npm start) &
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 街机游戏已在后台启动"
echo ""
echo "📋 服务地址："
echo "   MagiesGames 后端  → http://localhost:8000"
echo "   MagiesGames 前端  → http://localhost:5173"
for slug in "${SELECTED[@]}"; do
  echo "   $slug → http://localhost:${GAME_PORT_MAP[$slug]}"
done
echo ""
echo "👉 启动主项目前端："
echo "   cd $REPO/frontend && npm run dev"
echo ""
echo "按 Ctrl+C 停止所有后台游戏服务"

# 等待所有子进程
wait
