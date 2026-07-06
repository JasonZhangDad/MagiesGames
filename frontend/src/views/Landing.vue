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
const username = ref('')
const password = ref('')
const mode = ref('guest') // guest | login | register
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
    if (mode.value === 'login') {
      await user.login(username.value, password.value)
    } else if (mode.value === 'register') {
      await user.register(username.value, password.value, nickname.value)
    } else if (!user.profile) {
      await user.guestLogin(nickname.value)
    }
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
  username.value = ''
  password.value = ''
  mode.value = 'guest'
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
        <template v-if="user.profile && mode === 'guest'">
          <div class="welcome">
            <span class="avatar">{{ user.profile.avatar }}</span>
            <div>
              <div class="nick">
                {{ user.profile.nickname }}
                <span v-if="user.profile.registered" class="regtag">✓ 正式账号</span>
              </div>
              <div class="coin">💰 {{ user.profile.coin.toLocaleString() }}</div>
            </div>
          </div>
          <button class="btn btn-gold cta" :disabled="busy" @click="enter">进入大厅</button>
          <div class="minor">
            <button v-if="!user.profile.registered" class="btn btn-ghost small" @click="mode = 'register'">绑定正式账号</button>
            <button class="btn btn-ghost small" @click="switchAccount">切换账号</button>
          </div>
        </template>
        <template v-else>
          <div class="tabs">
            <button :class="{ on: mode === 'guest' }" @click="mode = 'guest'">游客</button>
            <button :class="{ on: mode === 'login' }" @click="mode = 'login'">登录</button>
            <button :class="{ on: mode === 'register' }" @click="mode = 'register'">注册</button>
          </div>
          <template v-if="mode === 'guest'">
            <input v-model="nickname" class="field" maxlength="12"
                   placeholder="起个响亮的昵称(可留空)" @keyup.enter="enter" />
          </template>
          <template v-else>
            <input v-model="username" class="field" maxlength="20" autocomplete="username"
                   placeholder="用户名(3-20 位字母数字)" @keyup.enter="enter" />
            <input v-model="password" class="field" type="password" maxlength="64"
                   :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
                   placeholder="密码(至少 6 位)" @keyup.enter="enter" />
            <input v-if="mode === 'register'" v-model="nickname" class="field" maxlength="12"
                   placeholder="昵称(可留空)" @keyup.enter="enter" />
            <p v-if="mode === 'register' && user.profile && !user.profile.registered" class="hint">
              将升级当前游客「{{ user.profile.nickname }}」,金币战绩全保留
            </p>
          </template>
          <button class="btn btn-gold cta" :disabled="busy" @click="enter">
            {{ busy ? '处理中…' : mode === 'login' ? '🔑 登录进入' : mode === 'register' ? '📝 注册进入' : '⚡ 游客秒进,立即开局' }}
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
.tabs { display: flex; gap: 6px; background: rgba(10, 16, 34, 0.5); border-radius: 12px; padding: 4px; }
.tabs button {
  flex: 1; border: none; background: transparent; color: var(--text-1);
  font: inherit; font-size: 14px; font-weight: 600; padding: 8px 0;
  border-radius: 9px; cursor: pointer; transition: all 0.15s;
}
.tabs button.on { background: rgba(53, 224, 255, 0.14); color: var(--text-0); }
.hint { color: var(--gold); font-size: 12.5px; text-align: left; }
.minor { display: flex; gap: 8px; justify-content: center; }
.regtag { color: var(--green); font-size: 11px; margin-left: 6px; }
.small { padding: 6px 12px; font-size: 13px; color: var(--text-1); }
.welcome { display: flex; align-items: center; gap: 12px; text-align: left; }
.avatar { font-size: 40px; }
.nick { font-weight: 700; font-size: 17px; }
.coin { color: var(--gold); font-size: 13.5px; margin-top: 2px; }
.feats { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; max-width: 560px; }
.foot { color: #55648f; font-size: 12px; margin-top: 4px; }
</style>
