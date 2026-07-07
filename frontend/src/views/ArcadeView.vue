<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const iframeRef = ref(null)
const loading = ref(true)
const error = ref(false)

// 游戏配置：slug -> { name, icon, desc, port, color }
const GAMES = {
  'bumper-cars': {
    name: '疯狂碰碰车',
    icon: '🚗',
    desc: '横冲直撞 · 物理竞速',
    port: 3001,
    color: 'rgba(255,200,60,0.15)',
    border: 'rgba(255,200,60,0.4)',
  },
  'neon-fps': {
    name: '霓虹竞技场',
    icon: '🔫',
    desc: '3D第一人称 · 赛博朋克',
    port: 3002,
    color: 'rgba(53,224,255,0.10)',
    border: 'rgba(53,224,255,0.4)',
  },
  'ice-climber': {
    name: '敲冰块大逃杀',
    icon: '🧊',
    desc: '多人平台 · 打冰存活',
    port: 3003,
    color: 'rgba(100,200,255,0.10)',
    border: 'rgba(100,200,255,0.4)',
  },
  'arena-brawl': {
    name: '2D卡通大乱斗',
    icon: '⚔️',
    desc: '多人混战 · 卡通竞技',
    port: 3004,
    color: 'rgba(255,107,157,0.10)',
    border: 'rgba(255,107,157,0.4)',
  },
  'bomb-party': {
    name: 'Q版炸弹人',
    icon: '💣',
    desc: '炸弹迷宫 · 经典玩法',
    port: 3005,
    color: 'rgba(139,123,255,0.10)',
    border: 'rgba(139,123,255,0.4)',
  },
}

// slug -> tools/dev-start.sh 里 GAME_DIR_MAP 的实际游戏目录名
const GAME_DIR_MAP = {
  'bumper-cars': 'crazy-bumper-cars',
  'neon-fps': 'neon-arena-fps',
  'ice-climber': 'ice-climber-arena',
  'arena-brawl': 'arena-brawl',
  'bomb-party': 'bomb-party',
}

const slug = computed(() => route.params.game)
const gameInfo = computed(() => GAMES[slug.value] || null)
const gameDir = computed(() => GAME_DIR_MAP[slug.value] || slug.value)

// 拼接游戏 URL：同域 /arcade-proxy/<slug>/ 走 Vite 代理到游戏端口
// 将 MagiesGames 昵称作为 URL 参数传入，游戏加载后注入脚本尝试预填
const nickname = computed(() => user.profile?.nickname || '')
const gameUrl = computed(() => {
  if (!gameInfo.value) return ''
  const nick = encodeURIComponent(nickname.value)
  return `/arcade/${slug.value}/?mg_nick=${nick}`
})

function onLoad() {
  loading.value = false
  // 尝试通过 postMessage 发送昵称（若游戏监听则可接收）
  try {
    iframeRef.value?.contentWindow?.postMessage(
      { type: 'MG_AUTH', nickname: nickname.value },
      '*'
    )
  } catch { /* 跨域静默失败 */ }
}

function onError() {
  loading.value = false
  error.value = true
}

function goBack() {
  router.push({ name: 'lobby' })
}

// 全屏锁定 body 滚动
onMounted(() => { document.body.style.overflow = 'hidden' })
onBeforeUnmount(() => { document.body.style.overflow = '' })
</script>

<template>
  <div class="arcade-wrap">
    <!-- 顶部工具栏 -->
    <div class="arcade-bar" v-if="gameInfo">
      <button class="back-btn" @click="goBack" title="返回大厅">
        ← 返回大厅
      </button>
      <div class="game-title">
        <span class="game-icon">{{ gameInfo.icon }}</span>
        <span class="game-name">{{ gameInfo.name }}</span>
        <span class="game-desc">{{ gameInfo.desc }}</span>
      </div>
      <div class="user-badge" v-if="user.profile">
        <span class="avatar">{{ user.profile.avatar }}</span>
        <span class="nick">{{ user.profile.nickname }}</span>
      </div>
    </div>

    <!-- 未找到游戏 -->
    <div v-if="!gameInfo" class="center-msg">
      <div class="err-icon">🎮</div>
      <div class="err-text">游戏不存在</div>
      <button class="btn btn-gold" @click="goBack">返回大厅</button>
    </div>

    <!-- 加载中遮罩 -->
    <div v-if="gameInfo && loading && !error" class="loading-mask">
      <div class="loading-ring"></div>
      <div class="loading-text">{{ gameInfo.icon }} 正在加载 {{ gameInfo.name }}...</div>
    </div>

    <!-- 连接错误提示 -->
    <div v-if="error" class="center-msg">
      <div class="err-icon">⚠️</div>
      <div class="err-text">游戏服务未启动</div>
      <div class="err-sub">请先在本地启动游戏服务（端口 {{ gameInfo?.port }}）</div>
      <div class="err-cmd">
        <code>cd tools/games-system-import/games/{{ gameDir }} && npm start</code>
      </div>
      <button class="btn btn-gold" style="margin-top:20px" @click="goBack">返回大厅</button>
    </div>

    <!-- 游戏 iframe -->
    <iframe
      v-if="gameInfo"
      ref="iframeRef"
      :src="gameUrl"
      class="game-frame"
      allow="autoplay; fullscreen; gamepad"
      @load="onLoad"
      @error="onError"
    ></iframe>
  </div>
</template>

<style scoped>
.arcade-wrap {
  --arcade-bar-core: 48px;
  --arcade-bar-height: calc(var(--arcade-bar-core) + var(--safe-t));
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #080d1a;
  z-index: 10;
}

/* 顶部工具栏 */
.arcade-bar {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: var(--safe-t) 16px 0;
  height: var(--arcade-bar-height);
  min-height: var(--arcade-bar-height);
  background: rgba(8, 13, 30, 0.95);
  border-bottom: 1px solid rgba(160, 190, 255, 0.12);
  backdrop-filter: blur(12px);
  z-index: 1;
}

.back-btn {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(160,190,255,0.15);
  color: #a0beff;
  padding: 6px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
  transition: all 0.2s;
}
.back-btn:hover {
  background: rgba(160,190,255,0.12);
  color: #fff;
}

.game-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}
.game-icon { font-size: 20px; }
.game-name { font-weight: 800; font-size: 15px; color: #fff; letter-spacing: 1px; }
.game-desc { font-size: 12px; color: #5c6b93; }

.user-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(245,193,69,0.08);
  border: 1px solid rgba(245,193,69,0.2);
  border-radius: 999px;
  padding: 4px 12px;
}
.avatar { font-size: 18px; }
.nick { font-size: 13px; color: #e5d080; font-weight: 600; }

/* 游戏 iframe：填满剩余高度 */
.game-frame {
  flex: 1;
  width: 100%;
  border: none;
  display: block;
  background: #080d1a;
}

/* 加载遮罩 */
.loading-mask {
  position: absolute;
  inset: var(--arcade-bar-height) 0 0 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  background: #080d1a;
  z-index: 2;
}
.loading-ring {
  width: 52px;
  height: 52px;
  border: 4px solid rgba(160,190,255,0.15);
  border-top-color: #35e0ff;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { color: #a0beff; font-size: 15px; }

/* 错误/不存在 */
.center-msg {
  position: absolute;
  inset: var(--arcade-bar-height) 0 0 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 2;
}
.err-icon { font-size: 60px; }
.err-text { font-size: 22px; font-weight: 700; color: #fff; }
.err-sub { font-size: 14px; color: #5c6b93; }
.err-cmd {
  margin-top: 8px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(160,190,255,0.12);
  border-radius: 10px;
  padding: 12px 20px;
}
.err-cmd code {
  font-family: ui-monospace, monospace;
  font-size: 13px;
  color: #35e0ff;
}

@media (max-width: 680px) {
  .arcade-bar { gap: 10px; padding-left: 10px; padding-right: 10px; }
  .back-btn { min-height: 36px; padding: 7px 10px; }
  .game-desc, .user-badge { display: none; }
  .game-title { min-width: 0; }
  .game-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
}
</style>
