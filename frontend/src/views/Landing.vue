<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useGameStore } from '../stores/game'
import { socket } from '../ws'
import { sfx } from '../sounds'
import { createLandingScene } from '../three/landingScene'

const router = useRouter()
const user = useUserStore()
const game = useGameStore()
const nickname = ref('')
const busy = ref(false)
const canvasEl = ref(null)
let scene3d = null

onMounted(() => {
  scene3d = createLandingScene(canvasEl.value)
  if (user.token) user.fetchMe()
})
onBeforeUnmount(() => scene3d?.dispose())

async function enter() {
  if (busy.value) return
  busy.value = true
  sfx.click()
  try {
    if (!user.profile) await user.guestLogin(nickname.value)
    socket.close()
    socket.connect(user.token)
    router.push({ name: 'lobby' })
  } catch (e) {
    game.toast(e.message, 'err')
  } finally {
    busy.value = false
  }
}

function switchAccount() {
  user.logout()
  nickname.value = ''
}
</script>

<template>
  <div class="landing">
    <canvas ref="canvasEl" class="bg3d" />
    <div class="hero">
      <div class="brand-badge chip">MAGIES · 3D 棋牌竞技大厅</div>
      <h1 class="title title-grad">斗地主</h1>
      <p class="slogan">沉浸式 3D 牌桌 · 服务端公正判定 · AI 秒补位</p>

      <div class="entry glass">
        <template v-if="user.profile">
          <div class="welcome">
            <span class="avatar">{{ user.profile.avatar }}</span>
            <div>
              <div class="nick">{{ user.profile.nickname }}</div>
              <div class="coin">💰 {{ user.profile.coin.toLocaleString() }}</div>
            </div>
          </div>
          <button class="btn btn-gold cta" :disabled="busy" @click="enter">进入大厅</button>
          <button class="btn btn-ghost small" @click="switchAccount">换个昵称</button>
        </template>
        <template v-else>
          <input
            v-model="nickname" class="field" maxlength="12"
            placeholder="起个响亮的昵称(可留空)" @keyup.enter="enter"
          />
          <button class="btn btn-gold cta" :disabled="busy" @click="enter">
            {{ busy ? '进入中…' : '⚡ 游客秒进,立即开局' }}
          </button>
        </template>
      </div>

      <div class="feats">
        <span class="chip">🃏 3D 发牌动画</span>
        <span class="chip">🛡️ 服务端防作弊</span>
        <span class="chip">🤖 AI 补位陪玩</span>
        <span class="chip">🔁 断线秒重连</span>
        <span class="chip">📱 手机平板全适配</span>
      </div>
      <p class="foot">纯娱乐虚拟积分 · 不涉及任何现金交易</p>
    </div>
  </div>
</template>

<style scoped>
.landing { position: relative; height: 100%; overflow: hidden; }
.bg3d { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
.hero {
  position: relative; z-index: 1; height: 100%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 18px; padding: 24px; text-align: center;
}
.brand-badge { letter-spacing: 2.5px; font-weight: 600; }
.title {
  font-size: clamp(64px, 15vw, 128px);
  font-weight: 900; letter-spacing: 6px; line-height: 1.08;
  filter: drop-shadow(0 10px 42px rgba(245, 193, 69, 0.3));
  animation: float-y 5s ease-in-out infinite;
}
.slogan { color: var(--text-1); font-size: clamp(14px, 2.4vw, 17px); letter-spacing: 3px; }
.entry {
  margin-top: 10px; padding: 22px; width: min(400px, 92vw);
  display: flex; flex-direction: column; gap: 12px;
}
.cta { font-size: 17px; padding: 15px 22px; animation: pulse-glow 2.4s ease-in-out infinite; }
.small { padding: 6px 12px; font-size: 13px; color: var(--text-1); }
.welcome { display: flex; align-items: center; gap: 12px; text-align: left; }
.avatar { font-size: 40px; }
.nick { font-weight: 700; font-size: 17px; }
.coin { color: var(--gold); font-size: 13.5px; margin-top: 2px; }
.feats { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 560px; }
.foot { color: #55648f; font-size: 12px; margin-top: 4px; }
</style>
