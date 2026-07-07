<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'

const KEY = 'mg_admin_key'
const key = ref(new URLSearchParams(location.search).get('key') || localStorage.getItem(KEY) || '')
const authed = ref(false)
const err = ref('')
const stats = ref(null)
const now = ref(new Date())
let pollTimer = null
let clockTimer = null

const GAME_LABEL = { ddz: '斗地主', mahjong: '血战麻将', gomoku: '五子棋', xiangqi: '中国象棋' }
const PHASE_LABEL = {
  waiting: '等待中', calling: '叫分', playing: '对局中', settled: '已结算',
  dingque: '定缺', exchange: '换三张',
}

async function load() {
  if (!key.value) return
  try {
    stats.value = await api.adminStats(key.value)
    authed.value = true
    err.value = ''
    localStorage.setItem(KEY, key.value)
  } catch (e) {
    err.value = e.message
    if (!authed.value) stats.value = null
  }
}

function enter() { load() }

const tiles = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    { label: '当前在线', value: s.online, hot: true },
    { label: '活跃房间', value: s.rooms.length, hot: true },
    { label: '今日对局', value: s.matches_today },
    { label: '累计对局', value: s.matches_total },
    { label: '注册用户', value: s.users_registered },
    { label: '总用户(含游客)', value: s.users_total },
  ]
})

const fmtTime = (t) => t ? new Date(t * 1000).toLocaleTimeString('zh-CN', { hour12: false }) : '—'

onMounted(() => {
  load()
  pollTimer = setInterval(load, 5000)
  clockTimer = setInterval(() => { now.value = new Date() }, 1000)
})
onBeforeUnmount(() => { clearInterval(pollTimer); clearInterval(clockTimer) })
</script>

<template>
  <div class="admin aurora-bg">
    <!-- 密钥门 -->
    <div v-if="!authed" class="gate">
      <div class="glass gatebox">
        <h2>🛠 运营后台</h2>
        <p class="dim">输入管理密钥进入大屏</p>
        <input v-model="key" type="password" class="field" placeholder="管理密钥"
               @keyup.enter="enter" />
        <button class="btn btn-gold" @click="enter">进入</button>
        <p v-if="err" class="errmsg">{{ err }}</p>
      </div>
    </div>

    <template v-else-if="stats">
      <header class="abar">
        <h1>🎰 Magies 运营大屏</h1>
        <div class="aclock">{{ now.toLocaleString('zh-CN', { hour12: false }) }}
          <span class="dot" title="每 5 秒自动刷新">●</span>
        </div>
      </header>

      <!-- 指标卡 -->
      <section class="tiles">
        <div v-for="t in tiles" :key="t.label" class="tile glass" :class="{ hot: t.hot }">
          <div class="tval">{{ (t.value ?? 0).toLocaleString() }}</div>
          <div class="tlabel">{{ t.label }}</div>
        </div>
      </section>

      <div class="cols">
        <!-- 活跃房间 -->
        <section class="panel glass">
          <h3>🏠 活跃房间 <span class="dim">({{ stats.rooms.length }})</span></h3>
          <div class="scroll-x">
            <table>
              <thead><tr><th>房号</th><th>游戏</th><th>阶段</th><th>真人</th><th>AI</th><th>观战</th><th>玩家</th></tr></thead>
              <tbody>
                <tr v-for="r in stats.rooms" :key="r.code">
                  <td class="mono">#{{ r.code }}{{ r.private ? ' 🔒' : '' }}</td>
                  <td>{{ GAME_LABEL[r.game] || r.game }}</td>
                  <td><span class="chip">{{ PHASE_LABEL[r.phase] || r.phase }}</span></td>
                  <td class="mono">{{ r.humans }}</td>
                  <td class="mono">{{ r.bots }}</td>
                  <td class="mono">{{ r.watchers }}</td>
                  <td class="pl">{{ r.players.map(p => (p.bot ? '🤖' : '👤') + p.nickname).join('、') }}</td>
                </tr>
                <tr v-if="!stats.rooms.length"><td colspan="7" class="empty">暂无活跃房间</td></tr>
              </tbody>
            </table>
          </div>

          <h3 class="mt">🕹️ 街机服务</h3>
          <div class="arcade-status">
            <span v-for="s in stats.arcade || []" :key="s.name" class="asvc" :class="{ up: s.up }">
              <i class="adot"></i>{{ s.name }}
            </span>
          </div>

          <h3 class="mt">🀄 对局分布</h3>
          <div class="dist">
            <div v-for="(n, g) in stats.matches_by_game" :key="g" class="dist-row">
              <span class="dlabel">{{ GAME_LABEL[g] || g }}</span>
              <div class="dbar-wrap">
                <div class="dbar" :style="{ width: (100 * n / Math.max(stats.matches_total, 1)) + '%' }"></div>
              </div>
              <span class="mono dnum">{{ n.toLocaleString() }}</span>
            </div>
          </div>
        </section>

        <!-- 对局流水 -->
        <section class="panel glass">
          <h3>📜 最近对局</h3>
          <div class="feed">
            <div v-for="m in stats.recent" :key="m.id" class="feed-row">
              <span class="mono ftime">{{ fmtTime(m.ended_at) }}</span>
              <span class="chip">{{ GAME_LABEL[m.game_type] || m.game_type }}</span>
              <span class="mono">#{{ m.room_code }}</span>
              <span class="fplayers">
                <template v-for="(p, i) in m.players" :key="i">
                  <b :class="p.delta_coin > 0 ? 'up' : p.delta_coin < 0 ? 'down' : ''">
                    {{ p.nickname }}{{ p.delta_coin > 0 ? ' +' + p.delta_coin : p.delta_coin < 0 ? ' ' + p.delta_coin : '' }}
                  </b><span v-if="i < m.players.length - 1" class="dim"> / </span>
                </template>
              </span>
            </div>
            <div v-if="!stats.recent.length" class="empty">还没有对局记录</div>
          </div>
        </section>

        <!-- 高手榜 -->
        <section class="panel glass slim">
          <h3>🏆 高手榜 TOP10</h3>
          <div v-for="(u, i) in stats.leaderboard" :key="u.id" class="rank-row">
            <span class="rank-no">{{ i + 1 }}</span>
            <span class="rav">{{ u.avatar }}</span>
            <span class="rname">{{ u.nickname }}</span>
            <span class="mono gold">💰{{ u.coin.toLocaleString() }}</span>
            <span class="mono dim">{{ u.wins }}胜{{ u.losses }}负</span>
          </div>
          <div v-if="!stats.leaderboard.length" class="empty">暂无上榜玩家</div>
        </section>
      </div>
      <p v-if="err" class="errmsg center">{{ err }}(展示为最后一次成功数据)</p>
    </template>
  </div>
</template>

<style scoped>
.admin { height: 100%; padding: 18px 22px 30px; overflow-y: auto; }
.gate { min-height: 80vh; display: flex; align-items: center; justify-content: center; }
.gatebox { padding: 32px 36px; text-align: center; width: min(360px, 92vw); display: flex; flex-direction: column; gap: 12px; }
.errmsg { color: var(--red); font-size: 13px; }
.errmsg.center { text-align: center; margin-top: 10px; }
.dim { color: var(--text-1); }

.abar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.abar h1 { font-size: 22px; letter-spacing: 1px; }
.aclock { font-family: ui-monospace, monospace; font-size: 15px; color: var(--text-1); }
.aclock .dot { color: var(--green); margin-left: 8px; animation: pulse-glow 2s infinite; }

.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px; }
.tile { padding: 18px 16px; border-radius: var(--r-md); text-align: center; }
.tile.hot .tval { color: var(--cyan); text-shadow: 0 0 24px rgba(53, 224, 255, 0.35); }
.tval { font-size: 34px; font-weight: 800; font-family: ui-monospace, monospace; }
.tlabel { color: var(--text-1); font-size: 13px; margin-top: 4px; }

.cols { display: grid; grid-template-columns: 1.3fr 1.2fr 0.9fr; gap: 12px; align-items: start; }
.panel { padding: 16px 18px; border-radius: var(--r-md); }
.panel h3 { font-size: 15px; margin-bottom: 10px; }
.panel h3.mt { margin-top: 18px; }
.scroll-x { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; color: var(--text-1); font-weight: 600; padding: 6px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; }
td { padding: 7px 8px; border-bottom: 1px solid rgba(160, 190, 255, 0.08); white-space: nowrap; }
td.pl { white-space: normal; min-width: 160px; font-size: 12px; color: var(--text-1); }
.mono { font-family: ui-monospace, monospace; }
.empty { color: #5c6b93; text-align: center; padding: 18px 0; font-size: 13px; }

.arcade-status { display: flex; flex-wrap: wrap; gap: 8px; }
.asvc {
  display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px;
  padding: 5px 12px; border-radius: 999px; color: #93a3c9;
  border: 1px solid rgba(160, 190, 255, 0.15); background: rgba(255, 92, 108, 0.06);
}
.asvc .adot { width: 8px; height: 8px; border-radius: 50%; background: #ff5c6c; }
.asvc.up { color: var(--green); border-color: rgba(61, 220, 151, 0.35); background: rgba(61, 220, 151, 0.06); }
.asvc.up .adot { background: var(--green); box-shadow: 0 0 8px rgba(61, 220, 151, 0.6); }

.dist { display: flex; flex-direction: column; gap: 8px; }
.dist-row { display: flex; align-items: center; gap: 10px; font-size: 13px; }
.dlabel { width: 72px; color: var(--text-1); }
.dbar-wrap { flex: 1; height: 10px; background: rgba(160, 190, 255, 0.08); border-radius: 5px; overflow: hidden; }
.dbar { height: 100%; border-radius: 5px 4px 4px 5px; background: linear-gradient(90deg, var(--cyan), var(--violet)); min-width: 2px; }
.dnum { min-width: 48px; text-align: right; }

.feed { display: flex; flex-direction: column; gap: 6px; max-height: 62vh; overflow-y: auto; }
.feed-row { display: flex; align-items: center; gap: 8px; padding: 7px 10px; background: rgba(10, 16, 34, 0.5); border-radius: 10px; font-size: 12.5px; flex-wrap: wrap; }
.ftime { color: var(--text-1); }
.fplayers b { font-weight: 600; }
.up { color: var(--green); }
.down { color: var(--red); }

.slim .rank-row { display: flex; align-items: center; gap: 8px; padding: 7px 4px; font-size: 13px; border-bottom: 1px solid rgba(160, 190, 255, 0.08); }
.rank-no { width: 20px; text-align: center; font-weight: 800; color: var(--gold); }
.rav { font-size: 18px; }
.rname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gold { color: var(--gold); }

@media (max-width: 1100px) { .cols { grid-template-columns: 1fr 1fr; } .slim { grid-column: span 2; } }
@media (max-width: 720px) { .cols { grid-template-columns: 1fr; } .slim { grid-column: auto; } .tval { font-size: 26px; } }
</style>
