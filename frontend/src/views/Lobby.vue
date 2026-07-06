<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'
import { sfx } from '../sounds'
import { useGameStore } from '../stores/game'
import { useUserStore } from '../stores/user'

const user = useUserStore()
const game = useGameStore()
const rooms = ref([])
const board = ref([])
const joinCode = ref('')
const showJoin = ref(false)
let timer = null

async function refresh() {
  try {
    const [r, b] = await Promise.all([api.rooms(), api.leaderboard()])
    rooms.value = r.rooms
    board.value = b.top.slice(0, 10)
  } catch { /* 轮询失败下轮重试 */ }
}

onMounted(() => {
  user.fetchMe()
  refresh()
  timer = setInterval(refresh, 5000)
})
onBeforeUnmount(() => clearInterval(timer))

function quick() { sfx.click(); game.quick() }
function create(priv) { sfx.click(); game.create(priv) }
function joinByCode() {
  const code = joinCode.value.trim()
  if (!/^\d{6}$/.test(code)) { game.toast('房间号是 6 位数字', 'err'); return }
  sfx.click()
  game.join(code)
}
function joinRoom(code) { sfx.click(); game.join(code) }

const comingSoon = [
  { icon: '⚫', name: '五子棋', tag: 'V1.5' },
  { icon: '♟️', name: '中国象棋', tag: 'V2.0' },
  { icon: '🀄', name: '麻将', tag: 'V3.0' },
]
const phaseLabel = { waiting: '等待中', calling: '叫分中', playing: '对局中', settled: '已结算' }
</script>

<template>
  <div class="lobby">
    <header class="topbar">
      <div class="brand">MAGIES <span class="sub">棋牌大厅</span></div>
      <div v-if="user.profile" class="me glass">
        <span class="avatar">{{ user.profile.avatar }}</span>
        <div class="meinfo">
          <div class="nick">{{ user.profile.nickname }}</div>
          <div class="stats">
            <span class="gold">💰{{ user.profile.coin.toLocaleString() }}</span>
            <span>🏆{{ user.profile.rank_point }}</span>
            <span>{{ user.profile.wins }}胜{{ user.profile.losses }}负</span>
          </div>
        </div>
      </div>
    </header>

    <main class="content">
      <!-- 主打游戏卡 -->
      <section class="hero-card glass">
        <div class="hero-left">
          <div class="game-badge">🃏 经典 · 3 人局</div>
          <h2 class="game-name title-grad">3D 斗地主</h2>
          <p class="game-desc">叫分抢地主 · 炸弹翻倍 · 春天 ×2<br />缺人 AI 秒补位,永不等待</p>
          <div class="hero-btns">
            <button class="btn btn-gold big" @click="quick">⚡ 快速匹配</button>
            <button class="btn btn-cyan" @click="create(false)">创建房间</button>
            <button class="btn btn-cyan" @click="create(true)">好友私密房</button>
            <button class="btn" @click="showJoin = !showJoin">输房号加入</button>
          </div>
          <div v-if="showJoin" class="joinrow">
            <input v-model="joinCode" class="field" placeholder="6 位房间号" maxlength="6"
                   inputmode="numeric" @keyup.enter="joinByCode" />
            <button class="btn btn-gold" @click="joinByCode">加入</button>
          </div>
        </div>
        <div class="hero-cards" aria-hidden="true">
          <span class="fc fc1">🂠</span><span class="fc fc2">🃏</span><span class="fc fc3">🂡</span>
        </div>
      </section>

      <div class="grid">
        <!-- 房间列表 -->
        <section class="panel glass">
          <h3>🔥 公开房间</h3>
          <div v-if="!rooms.length" class="empty">还没有房间,点「快速匹配」当房主!</div>
          <div v-for="r in rooms" :key="r.code" class="room-row">
            <div class="room-code">#{{ r.code }}</div>
            <div class="room-players">
              <span v-for="(p, i) in r.players" :key="i" :title="p.nickname">{{ p.avatar }}</span>
              <span v-for="i in r.seats_free" :key="'f' + i" class="free-seat">+</span>
            </div>
            <span class="chip">{{ phaseLabel[r.phase] || r.phase }}</span>
            <button class="btn joinbtn" :disabled="r.phase !== 'waiting' || !r.seats_free"
                    @click="joinRoom(r.code)">加入</button>
          </div>
        </section>

        <!-- 排行榜 -->
        <section class="panel glass">
          <h3>🏆 高手榜</h3>
          <div v-if="!board.length" class="empty">虚位以待,快来抢占榜首!</div>
          <div v-for="(u, i) in board" :key="u.id" class="rank-row">
            <span class="rank-no" :class="'r' + (i + 1)">{{ i + 1 }}</span>
            <span class="avatar-sm">{{ u.avatar }}</span>
            <span class="rank-nick">{{ u.nickname }}</span>
            <span class="rank-pt">🏆{{ u.rank_point }}</span>
          </div>
        </section>

        <!-- 敬请期待 -->
        <section class="panel glass">
          <h3>🚀 更多游戏</h3>
          <div class="soon-grid">
            <div v-for="g in comingSoon" :key="g.name" class="soon-card">
              <div class="soon-icon">{{ g.icon }}</div>
              <div class="soon-name">{{ g.name }}</div>
              <span class="chip">🔒 {{ g.tag }} 敬请期待</span>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.lobby { height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: calc(12px + var(--safe-t)) 20px 12px;
}
.brand { font-weight: 900; font-size: 20px; letter-spacing: 2px; color: var(--gold); }
.brand .sub { color: var(--text-1); font-size: 13px; font-weight: 500; margin-left: 6px; }
.me { display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-radius: 999px; }
.me .avatar { font-size: 26px; }
.nick { font-weight: 700; font-size: 14px; }
.stats { display: flex; gap: 10px; font-size: 12px; color: var(--text-1); margin-top: 2px; }
.stats .gold { color: var(--gold); }

.content { flex: 1; overflow-y: auto; padding: 6px 20px calc(24px + var(--safe-b)); }

.hero-card {
  position: relative; display: flex; justify-content: space-between; overflow: hidden;
  padding: 28px; margin-bottom: 16px;
  background: linear-gradient(120deg, rgba(245,193,69,0.10), rgba(53,224,255,0.07) 55%, rgba(139,123,255,0.09));
  border-color: rgba(245, 193, 69, 0.25);
}
.game-badge { color: var(--gold); font-size: 13px; letter-spacing: 2px; margin-bottom: 6px; }
.game-name { font-size: clamp(34px, 6vw, 52px); font-weight: 900; letter-spacing: 3px; }
.game-desc { color: var(--text-1); margin: 10px 0 18px; line-height: 1.7; font-size: 14px; }
.hero-btns { display: flex; flex-wrap: wrap; gap: 10px; }
.big { font-size: 17px; padding: 14px 30px; animation: pulse-glow 2.4s ease-in-out infinite; }
.joinrow { display: flex; gap: 10px; margin-top: 12px; max-width: 320px; }
.hero-cards { position: relative; min-width: 150px; }
.fc { position: absolute; font-size: 110px; filter: drop-shadow(0 12px 30px rgba(0,0,0,0.5)); }
.fc1 { right: 90px; top: 6px; transform: rotate(-14deg); animation: float-y 4.5s ease-in-out infinite; }
.fc2 { right: 45px; top: -4px; transform: rotate(2deg); animation: float-y 5s 0.4s ease-in-out infinite; }
.fc3 { right: 0; top: 8px; transform: rotate(15deg); animation: float-y 5.5s 0.8s ease-in-out infinite; }

.grid { display: grid; grid-template-columns: 1.35fr 1fr 1fr; gap: 16px; }
.panel { padding: 18px; min-height: 200px; }
.panel h3 { font-size: 15px; margin-bottom: 12px; letter-spacing: 1px; }
.empty { color: #5c6b93; font-size: 13px; padding: 26px 0; text-align: center; }

.room-row { display: flex; align-items: center; gap: 10px; padding: 9px 4px; border-bottom: 1px solid rgba(160,190,255,0.07); }
.room-code { font-weight: 700; font-family: ui-monospace, monospace; color: var(--cyan); }
.room-players { flex: 1; font-size: 18px; letter-spacing: 2px; }
.free-seat {
  display: inline-flex; width: 22px; height: 22px; border-radius: 50%;
  border: 1px dashed rgba(160,190,255,0.35); color: #5c6b93;
  align-items: center; justify-content: center; font-size: 13px; margin-left: 2px; vertical-align: 2px;
}
.joinbtn { padding: 7px 14px; font-size: 13px; }

.rank-row { display: flex; align-items: center; gap: 10px; padding: 8px 4px; border-bottom: 1px solid rgba(160,190,255,0.07); }
.rank-no { width: 22px; text-align: center; font-weight: 800; color: var(--text-1); font-style: italic; }
.rank-no.r1 { color: var(--gold); } .rank-no.r2 { color: #cfd8ea; } .rank-no.r3 { color: #d99a6c; }
.avatar-sm { font-size: 20px; }
.rank-nick { flex: 1; font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-pt { color: var(--gold); font-size: 12.5px; }

.soon-grid { display: flex; flex-direction: column; gap: 10px; }
.soon-card {
  display: flex; align-items: center; gap: 12px; padding: 12px;
  border: 1px solid rgba(160,190,255,0.08); border-radius: var(--r-md);
  background: rgba(10,16,34,0.35); opacity: 0.75;
}
.soon-icon { font-size: 28px; }
.soon-name { flex: 1; font-weight: 600; font-size: 14.5px; }

@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
  .hero-cards { display: none; }
  .hero-card { padding: 22px; }
}
</style>
