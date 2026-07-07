<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { sfx } from '../sounds'
import { useGameStore } from '../stores/game'
import { useUserStore } from '../stores/user'
import { socket } from '../ws'

// 街机游戏配置
const ARCADE_GAMES = [
  { slug: 'bumper-cars', name: '疯狂碰碰车', icon: '🚗', desc: '横冲直撞物理竞速', tag: '多人', color: '#ffc83c', bg: 'rgba(255,200,60,0.08)', border: 'rgba(255,200,60,0.25)' },
  { slug: 'neon-fps',    name: '霓虹竞技场', icon: '🔫', desc: '3D第一人称射击',   tag: '多人', color: '#35e0ff', bg: 'rgba(53,224,255,0.08)',  border: 'rgba(53,224,255,0.25)' },
  { slug: 'ice-climber', name: '敲冰块大逃杀',icon: '🧊', desc: '多人平台生存竞技', tag: '多人', color: '#7ad4ff', bg: 'rgba(100,200,255,0.08)', border: 'rgba(100,200,255,0.25)' },
  { slug: 'arena-brawl', name: '2D卡通大乱斗',icon: '⚔️', desc: '卡通混战竞技',    tag: '多人', color: '#ff6b9d', bg: 'rgba(255,107,157,0.08)', border: 'rgba(255,107,157,0.25)' },
  { slug: 'bomb-party',  name: 'Q版炸弹人',  icon: '💣', desc: '炸弹迷宫经典玩法', tag: '多人', color: '#a78bff', bg: 'rgba(139,123,255,0.08)', border: 'rgba(139,123,255,0.25)' },
]

const router = useRouter()

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

function quick(g = 'ddz') { sfx.click(); game.quick(g) }
function create(priv, g = 'ddz') { sfx.click(); game.create(priv, g) }
function joinByCode() {
  const code = joinCode.value.trim()
  if (!/^\d{6}$/.test(code)) { game.toast('房间号是 6 位数字', 'err'); return }
  sfx.click()
  game.join(code)
}
function joinRoom(code) { sfx.click(); game.join(code) }
function watchRoom(code) { sfx.click(); game.watch(code) }
function logout() {
  socket.close()
  user.logout()
  router.push({ name: 'landing' })
}
function openArcade(slug) {
  sfx.click()
  router.push({ name: 'arcade', params: { game: slug } })
}

const comingSoon = []
const phaseLabel = {
  waiting: '等待中', calling: '叫分中', exchange: '换三张', dingque: '定缺中',
  playing: '对局中', settled: '已结算',
}
const gameLabel = { ddz: '斗地主', mahjong: '麻将', gomoku: '五子棋', xiangqi: '象棋' }
</script>

<template>
  <div class="lobby">
    <header class="topbar">
      <div class="brand">MAGIES <span class="sub">棋牌大厅</span></div>
      <div v-if="user.profile" class="me glass">
        <span class="avatar">{{ user.profile.avatar }}</span>
        <div class="meinfo">
          <div class="nick">
            {{ user.profile.nickname }}
            <span v-if="user.profile.registered" class="regtag" title="正式账号">✓</span>
            <span v-else class="guesttag">游客</span>
          </div>
          <div class="stats">
            <span class="gold">💰{{ user.profile.coin.toLocaleString() }}</span>
            <span>🏆{{ user.profile.rank_point }}</span>
            <span>{{ user.profile.wins }}胜{{ user.profile.losses }}负</span>
          </div>
        </div>
        <button class="logout" title="退出登录" @click="logout">⎋</button>
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
            <button class="btn btn-gold big" @click="quick()">⚡ 快速匹配</button>
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
          <span class="fc fc1 pcard back-card"><b>M</b></span>
          <span class="fc fc2 pcard"><i class="red">♥</i><b class="red">A</b></span>
          <span class="fc fc3 pcard"><i>♠</i><b>K</b></span>
        </div>
      </section>

      <!-- 四川麻将 -->
      <section class="hero-card mj glass">
        <div class="hero-left">
          <div class="game-badge mjb">🀄 四川 · 4 人局</div>
          <h2 class="game-name title-grad">血战麻将</h2>
          <p class="game-desc">定缺 · 碰杠胡 · 血战到底<br />胡牌离场继续打,一炮多响</p>
          <div class="hero-btns">
            <button class="btn btn-gold big" @click="quick('mahjong')">⚡ 快速匹配</button>
            <button class="btn btn-cyan" @click="create(false, 'mahjong')">创建房间</button>
            <button class="btn btn-cyan" @click="create(true, 'mahjong')">好友私密房</button>
          </div>
        </div>
        <div class="hero-cards" aria-hidden="true">
          <span class="fc fc1 mjtile"><b class="mj-num">五</b><b class="mj-wan">萬</b></span>
          <span class="fc fc2 mjtile"><i class="mj-coin"></i></span>
          <span class="fc fc3 mjtile tiao"><i class="mj-bar"></i><i class="mj-bar mid"></i><i class="mj-bar"></i></span>
        </div>
      </section>

      <!-- 五子棋 -->
      <section class="hero-card gmk glass">
        <div class="hero-left">
          <div class="game-badge gmkb">⚫ 对弈 · 2 人局</div>
          <h2 class="game-name title-grad">3D 五子棋</h2>
          <p class="game-desc">黑先白后 · 连五即胜<br />悬停预览落点,快节奏对弈</p>
          <div class="hero-btns">
            <button class="btn btn-gold big" @click="quick('gomoku')">⚡ 快速匹配</button>
            <button class="btn btn-cyan" @click="create(false, 'gomoku')">创建房间</button>
            <button class="btn btn-cyan" @click="create(true, 'gomoku')">好友私密房</button>
          </div>
        </div>
        <div class="hero-cards" aria-hidden="true">
          <span class="fc fc1 gstone black"></span>
          <span class="fc fc2 gstone white"></span>
          <span class="fc fc3 gstone black"></span>
        </div>
      </section>

      <!-- 中国象棋 -->
      <section class="hero-card xq glass">
        <div class="hero-left">
          <div class="game-badge xqb">♟ 对弈 · 2 人局</div>
          <h2 class="game-name title-grad">3D 中国象棋</h2>
          <p class="game-desc">楚河汉界 · 红先黑后<br />绝杀困毙皆负,经典博弈</p>
          <div class="hero-btns">
            <button class="btn btn-gold big" @click="quick('xiangqi')">⚡ 快速匹配</button>
            <button class="btn btn-cyan" @click="create(false, 'xiangqi')">创建房间</button>
            <button class="btn btn-cyan" @click="create(true, 'xiangqi')">好友私密房</button>
          </div>
        </div>
        <div class="hero-cards" aria-hidden="true">
          <span class="fc fc1 xqpiece red-p">帥</span>
          <span class="fc fc2 xqpiece">將</span>
          <span class="fc fc3 xqpiece red-p">馬</span>
        </div>
      </section>

      <!-- 街机游戏区 -->
      <section class="arcade-section">
        <div class="arcade-header">
          <h3 class="arcade-title">🕹️ 街机游戏</h3>
          <span class="arcade-sub">登录即玩 · 零门槛多人游戏</span>
        </div>
        <div class="arcade-grid">
          <div
            v-for="g in ARCADE_GAMES" :key="g.slug"
            class="arcade-card glass"
            :style="{ background: g.bg, borderColor: g.border }"
            @click="openArcade(g.slug)"
          >
            <div class="ac-icon">{{ g.icon }}</div>
            <div class="ac-info">
              <div class="ac-name" :style="{ color: g.color }">{{ g.name }}</div>
              <div class="ac-desc">{{ g.desc }}</div>
            </div>
            <span class="ac-tag" :style="{ color: g.color, borderColor: g.border }">{{ g.tag }}</span>
            <div class="ac-arrow">▶</div>
          </div>
        </div>
      </section>

      <div class="grid">
        <!-- 房间列表 -->
        <section class="panel glass">
          <h3>🔥 公开房间</h3>
          <div v-if="!rooms.length" class="empty">还没有房间,点「快速匹配」当房主!</div>
          <div v-for="r in rooms" :key="r.code" class="room-row">
            <div class="room-code">#{{ r.code }}</div>
            <span class="chip">{{ gameLabel[r.game] || r.game }}</span>
            <div class="room-players">
              <span v-for="(p, i) in r.players" :key="i" :title="p.nickname">{{ p.avatar }}</span>
              <span v-for="i in r.seats_free" :key="'f' + i" class="free-seat">+</span>
            </div>
            <span class="chip">{{ phaseLabel[r.phase] || r.phase }}</span>
            <button class="btn joinbtn" :disabled="r.phase !== 'waiting' || !r.seats_free"
                    @click="joinRoom(r.code)">加入</button>
            <button class="btn joinbtn" @click="watchRoom(r.code)">👁 观战</button>
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
        <section class="panel glass" v-if="comingSoon.length">
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
.regtag { color: var(--green); font-size: 12px; }
.guesttag {
  color: var(--text-1); font-size: 10.5px; border: 1px solid var(--line);
  border-radius: 999px; padding: 1px 7px; margin-left: 4px; vertical-align: 1px;
}
.logout {
  border: none; background: transparent; color: var(--text-1); cursor: pointer;
  font-size: 17px; padding: 4px 6px; border-radius: 8px;
}
.logout:hover { color: var(--red); background: rgba(255, 92, 108, 0.1); }
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
.hero-card.mj {
  background: linear-gradient(120deg, rgba(61, 220, 151, 0.09), rgba(53, 224, 255, 0.06) 55%, rgba(245, 193, 69, 0.08));
  border-color: rgba(61, 220, 151, 0.25);
}
.game-badge.mjb { color: var(--green); }
.hero-card.gmk {
  background: linear-gradient(120deg, rgba(139, 123, 255, 0.10), rgba(53, 224, 255, 0.06) 55%, rgba(255, 107, 157, 0.08));
  border-color: rgba(139, 123, 255, 0.3);
}
.game-badge.gmkb { color: #b9adff; }
.hero-card.xq {
  background: linear-gradient(120deg, rgba(255, 107, 107, 0.10), rgba(245, 193, 69, 0.06) 55%, rgba(53, 224, 255, 0.07));
  border-color: rgba(255, 107, 107, 0.3);
}
.game-badge.xqb { color: #ff9d8a; }
.game-name { font-size: clamp(34px, 6vw, 52px); font-weight: 900; letter-spacing: 3px; }
.game-desc { color: var(--text-1); margin: 10px 0 18px; line-height: 1.7; font-size: 14px; }
.hero-btns { display: flex; flex-wrap: wrap; gap: 10px; }
.big { font-size: 17px; padding: 14px 30px; animation: pulse-glow 2.4s ease-in-out infinite; }
.joinrow { display: flex; gap: 10px; margin-top: 12px; max-width: 320px; }
.hero-cards { position: relative; min-width: 190px; }
.fc { position: absolute; display: inline-flex; align-items: center; justify-content: center; }
.fc1 { right: 118px; top: 12px; transform: rotate(-14deg); animation: float-y 4.5s ease-in-out infinite; }
.fc2 { right: 60px; top: 0; transform: rotate(2deg); animation: float-y 5s 0.4s ease-in-out infinite; z-index: 1; }
.fc3 { right: 4px; top: 14px; transform: rotate(15deg); animation: float-y 5.5s 0.8s ease-in-out infinite; }

/* 精制装饰小件:扑克 */
.pcard {
  width: 78px; height: 108px; border-radius: 10px; flex-direction: column; gap: 0;
  background: linear-gradient(160deg, #ffffff, #eef0f8);
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.55), inset 0 0 0 1px rgba(35, 42, 77, 0.15);
}
.pcard b { font-size: 42px; font-weight: 900; color: #232a4d; font-family: Georgia, serif; line-height: 1; }
.pcard i { font-style: normal; font-size: 30px; color: #232a4d; line-height: 1.1; }
.pcard .red { color: #e23b4e; }
.back-card {
  background: linear-gradient(140deg, #1b2350, #2a1f66 55%, #131a3e);
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.55), inset 0 0 0 3px rgba(245, 193, 69, 0.55);
}
.back-card b { color: #f5c145; font-size: 52px; text-shadow: 0 0 16px rgba(245, 193, 69, 0.65); }

/* 精制装饰小件:麻将(万/筒/条,四川麻将无字牌) */
.mjtile {
  width: 78px; height: 104px; border-radius: 12px; flex-direction: column;
  background: linear-gradient(180deg, #fdfaf0, #ece1c6);
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.55),
    inset 0 -5px 9px rgba(120, 95, 45, 0.20), inset 0 2px 3px rgba(255, 255, 255, 0.95);
}
.mjtile.tiao { flex-direction: row; }
.mj-num { font-size: 36px; font-weight: 900; color: #c02f2f; font-family: "Kaiti SC", "STKaiti", serif; line-height: 1.15; }
.mj-wan { font-size: 32px; font-weight: 900; color: #23232b; font-family: "Kaiti SC", "STKaiti", serif; line-height: 1.1; }
.mj-coin {
  width: 48px; height: 48px; border-radius: 50%; border: 7px solid #2c4a88;
  background: radial-gradient(circle at 36% 30%, #e05b52, #8e1f1f);
  box-shadow: inset 0 0 0 3px rgba(255, 255, 255, 0.75);
}
.mj-bar {
  width: 13px; height: 54px; border-radius: 7px; margin: 0 3px;
  background: linear-gradient(90deg, #14573a, #37a06b 40%, #37a06b 60%, #14573a);
}
.mj-bar.mid { background: linear-gradient(90deg, #8e1f1f, #e05b52 40%, #e05b52 60%, #8e1f1f); }

/* 精制装饰小件:五子棋 */
.gstone { width: 84px; height: 84px; border-radius: 50%; box-shadow: 0 16px 32px rgba(0, 0, 0, 0.6); }
.gstone.black { background: radial-gradient(circle at 34% 28%, #6a7080, #14161c 66%); }
.gstone.white { background: radial-gradient(circle at 34% 28%, #ffffff, #cfc9b8 72%); }

/* 精制装饰小件:象棋 */
.xqpiece {
  width: 88px; height: 88px; border-radius: 50%; color: #26221c;
  background: radial-gradient(circle at 40% 32%, #f7ecd2, #dcc494 78%);
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.6), inset 0 0 0 4px currentColor,
    inset 0 0 0 7px rgba(247, 236, 210, 0.95);
  font-family: "Kaiti SC", "STKaiti", serif; font-size: 42px; font-weight: 900;
}
.xqpiece.red-p { color: #c22c22; }

/* 街机游戏区 */
.arcade-section { margin-bottom: 20px; }
.arcade-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; }
.arcade-title { font-size: 15px; margin: 0; letter-spacing: 1px; }
.arcade-sub { font-size: 12px; color: #5c6b93; }
.arcade-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.arcade-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 12px;
  border-radius: var(--r-md);
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s;
  border-width: 1px;
  border-style: solid;
}
.arcade-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 28px rgba(0,0,0,0.35);
}
.ac-icon { font-size: 28px; flex-shrink: 0; }
.ac-info { flex: 1; min-width: 0; }
.ac-name { font-weight: 800; font-size: 13px; letter-spacing: 0.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ac-desc { font-size: 11px; color: #5c6b93; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ac-tag { font-size: 10px; border: 1px solid; border-radius: 999px; padding: 1px 7px; flex-shrink: 0; }
.ac-arrow { font-size: 11px; color: rgba(160,190,255,0.4); flex-shrink: 0; }

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
  .arcade-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 500px) {
  .arcade-grid { grid-template-columns: 1fr; }
}
</style>
