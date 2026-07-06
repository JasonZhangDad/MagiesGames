<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { isMuted, sfx, toggleMute } from '../sounds'
import { useGameStore } from '../stores/game'
import { useUserStore } from '../stores/user'
import { TableScene } from '../three/tableScene'

const game = useGameStore()
const user = useUserStore()
const canvasEl = ref(null)
const muted = ref(isMuted())
const lowSpec = ref(localStorage.getItem('mg_lowspec') === '1')
const showSettle = ref(false)
const settle = ref(null)
const bubbles = reactive({})
const now = ref(Date.now() / 1000)
let scene = null
let clockTimer = null

const room = computed(() => game.room)
const mySeat = computed(() => room.value?.my_seat)
const phase = computed(() => room.value?.phase)
const myTurn = computed(() => room.value && room.value.current === mySeat.value && mySeat.value !== null)
const me = computed(() => (mySeat.value !== null && room.value) ? room.value.seats[mySeat.value] : null)

const relOf = (seat) => (seat - mySeat.value + 3) % 3
const seatAtRel = (rel) => {
  if (mySeat.value === null || !room.value) return null
  return room.value.seats[(mySeat.value + rel) % 3]
}
const seatNoAtRel = (rel) => (mySeat.value + rel) % 3

const countdown = computed(() => {
  if (!room.value?.deadline) return null
  return Math.max(0, Math.ceil(room.value.deadline - now.value))
})

const callOptions = computed(() => {
  const max = room.value?.max_call ?? 0
  return [1, 2, 3].filter(s => s > max)
})

const multiplier = computed(() => {
  if (!room.value) return 1
  return 2 ** (room.value.bombs || 0)
})

// ---------- 场景生命周期 ----------

onMounted(() => {
  scene = new TableScene(canvasEl.value, {
    onToggleCard: (id) => {
      if (phase.value !== 'playing' && phase.value !== 'calling') return
      sfx.select()
      game.toggleSelect(id)
    },
  })
  scene.setLowSpec(lowSpec.value)
  if (import.meta.env.DEV) window.__ts = scene
  syncFromState(room.value, true)
  clockTimer = setInterval(() => { now.value = Date.now() / 1000 }, 250)
})

onBeforeUnmount(() => {
  clearInterval(clockTimer)
  scene?.dispose()
  scene = null
})

// ---------- 快照同步(唯一可信源) ----------

function syncFromState(st, cold = false) {
  if (!scene || !st) return
  const hand = st.my_hand || []
  scene.setMyHand(hand)
  game.selected = game.selected.filter(c => hand.includes(c))
  scene.setSelected(game.selected)
  if (st.landlord !== null && st.bottom) scene.setBottom(st.bottom, true)
  else if (st.phase === 'calling' || st.phase === 'playing') scene.setBottom(null, false)
  if (!st.last) scene.clearTricks()
  else if (cold) scene.setTrick(relOf(st.last.seat), st.last.cards, { animate: false })
  if (cold && st.phase === 'settled' && st.result) {
    settle.value = st.result
    showSettle.value = true
  }
}

watch(room, (st) => syncFromState(st))
watch(() => game.selected.slice(), (sel) => scene?.setSelected(sel))
watch(() => game.hintCards, (cards) => {
  if (cards?.length) {
    game.selected = [...cards]
    game.hintCards = null
  }
})

// ---------- 事件动画 ----------

function bubble(seat, text, ms = 2400) {
  bubbles[seat] = { text, id: Date.now() }
  setTimeout(() => {
    if (bubbles[seat] && Date.now() - bubbles[seat].id >= ms - 20) delete bubbles[seat]
  }, ms)
}

// 逐条消费事件队列(watcher 合并没关系,这里把积压的全部处理掉)
watch(() => game.events.length, () => {
  while (game.events.length) handleEvent(game.events.shift())
})

function handleEvent(e) {
  if (!e || !scene) return
  switch (e.e) {
    case 'deal':
    case 'redeal': {
      showSettle.value = false
      settle.value = null
      Object.keys(bubbles).forEach(k => delete bubbles[k])
      game.selected = []
      scene.clearTricks()
      if (e.e === 'redeal') game.toast('无人叫分,重新发牌')
      setTimeout(() => {
        scene?.setMyHand(room.value?.my_hand || [], { deal: true })
        scene?.setBottom(null, false)
      }, 60)
      sfx.deal()
      break
    }
    case 'call':
      bubble(e.seat, e.score === 0 ? '不叫' : `叫 ${e.score} 分!`)
      sfx.click()
      break
    case 'landlord': {
      const s = room.value?.seats?.[e.seat]
      game.toast(`👑 ${s?.nickname ?? ''} 成为地主,底分 ${e.base}`)
      scene.revealBottom(e.bottom)
      sfx.landlord()
      break
    }
    case 'play': {
      scene.setTrick(relOf(e.seat), e.cards, { animate: true })
      bubble(e.seat, e.kind_label)
      if (e.kind === 'bomb' || e.kind === 'rocket') {
        scene.bombFlash()
        sfx.bomb()
      } else {
        sfx.play()
      }
      if (e.seat === mySeat.value) game.selected = []
      break
    }
    case 'pass':
      bubble(e.seat, '不出')
      sfx.pass()
      break
    case 'settle': {
      settle.value = e.result
      showSettle.value = true
      const myDelta = e.result.coin_deltas[mySeat.value] ?? 0
      scene.celebrate(myDelta >= 0)
      myDelta >= 0 ? sfx.win() : sfx.lose()
      user.fetchMe()
      break
    }
    case 'chat':
      bubble(e.seat, e.text, 3000)
      break
    case 'bot_fill': {
      game.toast(`🤖 ${e.nickname} 加入补位`)
      break
    }
    case 'auto':
      if (e.seat === mySeat.value) game.toast(e.on ? '已开启托管,AI 代打' : '已取消托管')
      break
    case 'offline': bubble(e.seat, '📴 掉线了'); break
    case 'online': bubble(e.seat, '🔌 回来了'); break
  }
}

// ---------- 操作 ----------

function doPlay() {
  if (!game.selected.length) { game.toast('先选牌再出'); return }
  game.playSelected()
}
function doMute() { muted.value = toggleMute() }
function doLowSpec() {
  lowSpec.value = !lowSpec.value
  localStorage.setItem('mg_lowspec', lowSpec.value ? '1' : '0')
  scene?.setLowSpec(lowSpec.value)
}
function copyCode() {
  navigator.clipboard?.writeText(room.value.code)
  game.toast(`房间号 ${room.value.code} 已复制,发给好友吧`)
}
function nextRound() { game.ready(true); sfx.click() }
function backLobby() { game.leave() }
const quickChats = ['👍', '🔥', '😭', '😤', '快点吧~', '你真棒!', '大意了!']

const roleLabel = { landlord: '地主', farmer: '农民' }
</script>

<template>
  <div class="gamepage" v-if="room">
    <canvas ref="canvasEl" class="stage" />

    <!-- 顶栏 -->
    <header class="hud top">
      <div class="left-c">
        <button class="btn icon" @click="backLobby" title="离开房间">←</button>
        <button class="chip code" @click="copyCode">🏠 {{ room.code }} ⧉</button>
        <span class="chip" v-if="room.base">底分 {{ room.base }} · ×{{ multiplier }}<template v-if="room.bombs"> 💣{{ room.bombs }}</template></span>
      </div>
      <div class="right-c">
        <button class="btn icon" @click="doMute" :title="muted ? '开声音' : '静音'">{{ muted ? '🔇' : '🔊' }}</button>
        <button class="btn icon" :class="{ on: lowSpec }" @click="doLowSpec" title="低配模式">🍃</button>
        <button v-if="phase === 'playing' || phase === 'calling'" class="btn icon" :class="{ on: me?.auto }"
                @click="game.setAuto(!me?.auto)" title="托管">🤖</button>
      </div>
    </header>

    <!-- 左右对手座位牌 -->
    <div v-for="rel in [2, 1]" :key="rel" class="plate glass" :class="rel === 1 ? 'right' : 'left'">
      <template v-if="seatAtRel(rel)">
        <div class="pav" :class="{ turn: room.current === seatNoAtRel(rel) }">
          <span>{{ seatAtRel(rel).avatar }}</span>
          <i v-if="seatAtRel(rel).role === 'landlord'" class="crown">👑</i>
        </div>
        <div class="pinfo">
          <div class="pname">
            {{ seatAtRel(rel).nickname }}
            <span v-if="!seatAtRel(rel).connected" title="掉线">📴</span>
            <span v-else-if="seatAtRel(rel).auto" title="托管">🤖</span>
          </div>
          <div class="pmeta">
            <span class="gold">💰{{ (seatAtRel(rel).coin ?? 0).toLocaleString() }}</span>
          </div>
        </div>
        <div class="pright">
          <span v-if="phase === 'playing' || phase === 'settled'" class="cards-left">🂠{{ seatAtRel(rel).cards_left }}</span>
          <span v-else-if="seatAtRel(rel).ready" class="okay">✓ 已准备</span>
          <span v-if="room.current === seatNoAtRel(rel) && countdown !== null" class="cd">{{ countdown }}</span>
        </div>
        <transition name="fade">
          <div v-if="bubbles[seatNoAtRel(rel)]" class="bubble">{{ bubbles[seatNoAtRel(rel)].text }}</div>
        </transition>
      </template>
      <template v-else><div class="pempty">等待玩家…</div></template>
    </div>

    <!-- 我的气泡 -->
    <transition name="fade">
      <div v-if="mySeat !== null && bubbles[mySeat]" class="bubble mine">{{ bubbles[mySeat].text }}</div>
    </transition>

    <!-- 等待开局面板 -->
    <div v-if="phase === 'waiting'" class="waitbox glass">
      <h2>房间 <b class="title-grad">{{ room.code }}</b></h2>
      <p class="dim">凑满 3 人开局 · 点准备后 AI 数秒内补位</p>
      <div class="wseats">
        <div v-for="(s, i) in room.seats" :key="i" class="wseat" :class="{ filled: s }">
          <template v-if="s">
            <span class="wav">{{ s.avatar }}</span>
            <span class="wname">{{ s.nickname }}</span>
            <span class="chip" :class="{ ok: s.ready }">{{ s.ready ? '已准备' : '未准备' }}</span>
          </template>
          <template v-else><span class="wav dim">➕</span><span class="dim">空位</span></template>
        </div>
      </div>
      <div class="wbtns">
        <button v-if="!me?.ready" class="btn btn-gold big" @click="game.ready(true)">✓ 准备开局</button>
        <button v-else class="btn" @click="game.ready(false)">取消准备</button>
        <button class="btn btn-ghost" @click="copyCode">邀请好友</button>
      </div>
    </div>

    <!-- 底部操作区 -->
    <footer class="hud bottom">
      <div class="my-plate" v-if="me">
        <div class="pav big" :class="{ turn: myTurn }">
          <span>{{ me.avatar }}</span>
          <i v-if="me.role === 'landlord'" class="crown">👑</i>
        </div>
        <div class="pinfo">
          <div class="pname">{{ me.nickname }}</div>
          <div class="pmeta"><span class="gold">💰{{ (me.coin ?? 0).toLocaleString() }}</span></div>
        </div>
        <span v-if="myTurn && countdown !== null" class="cd big">{{ countdown }}</span>
      </div>

      <!-- 叫分 -->
      <div v-if="phase === 'calling' && myTurn" class="actions">
        <button class="btn act" @click="game.call(0)">不叫</button>
        <button v-for="s in callOptions" :key="s" class="btn act" :class="s === 3 ? 'btn-gold' : 'btn-cyan'"
                @click="game.call(s)">{{ s }} 分</button>
      </div>

      <!-- 出牌 -->
      <div v-else-if="phase === 'playing' && myTurn && !me?.auto" class="actions">
        <button class="btn act" @click="game.hint()">💡 提示</button>
        <button class="btn act" :disabled="room.leading" @click="game.pass()">不出</button>
        <button class="btn act btn-gold" :disabled="!game.selected.length" @click="doPlay">
          出牌{{ game.selected.length ? ` (${game.selected.length})` : '' }}
        </button>
      </div>

      <div v-else-if="(phase === 'playing' || phase === 'calling') && me?.auto" class="actions">
        <button class="btn act btn-cyan" @click="game.setAuto(false)">🤖 托管中,点击接管</button>
      </div>

      <div v-else-if="(phase === 'playing' || phase === 'calling') && !myTurn" class="actions dim-hint">
        等待 {{ room.seats[room.current]?.nickname ?? '' }} 操作…
      </div>

      <!-- 快捷聊天 -->
      <div class="chatbar" v-if="phase !== 'waiting'">
        <button v-for="c in quickChats" :key="c" class="chatchip" @click="game.chat(c)">{{ c }}</button>
      </div>
    </footer>

    <!-- 结算弹窗 -->
    <transition name="fade">
      <div v-if="showSettle && settle" class="modal-mask">
        <div class="settle glass">
          <h2 :class="settle.coin_deltas[mySeat] >= 0 ? 'winh' : 'loseh'">
            {{ settle.coin_deltas[mySeat] >= 0 ? '🏆 胜利!' : '💔 惜败' }}
          </h2>
          <div class="badges">
            <span class="chip">{{ roleLabel[settle.winner_role] }}赢</span>
            <span class="chip">底分 {{ settle.base }}</span>
            <span class="chip">倍数 ×{{ settle.multiplier }}</span>
            <span v-if="settle.bombs" class="chip">💣 炸弹 {{ settle.bombs }}</span>
            <span v-if="settle.spring" class="chip spring">🌸 春天 ×2</span>
          </div>
          <div class="srows">
            <div v-for="(s, i) in room.seats" :key="i" class="srow" :class="{ meRow: i === mySeat }">
              <span class="wav">{{ s?.avatar }}</span>
              <span class="sname">{{ s?.nickname }}<i v-if="settle && i === room.landlord"> 👑</i></span>
              <span class="sdelta" :class="settle.coin_deltas[i] >= 0 ? 'up' : 'down'">
                {{ settle.coin_deltas[i] >= 0 ? '+' : '' }}{{ settle.coin_deltas[i].toLocaleString() }}
              </span>
            </div>
          </div>
          <div class="sbtns">
            <button v-if="!me?.ready" class="btn btn-gold big" @click="nextRound">🔄 再来一局</button>
            <button v-else class="btn" disabled>等待其他玩家…</button>
            <button class="btn btn-ghost" @click="backLobby">返回大厅</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
  <div v-else class="gamepage loading"><div class="chip">正在进入房间…</div></div>
</template>

<style scoped>
.gamepage { position: relative; height: 100%; overflow: hidden; }
.gamepage.loading { display: flex; align-items: center; justify-content: center; }
.stage { position: absolute; inset: 0; width: 100%; height: 100%; display: block; touch-action: none; }

.hud { position: absolute; left: 0; right: 0; z-index: 5; display: flex; justify-content: space-between; padding: 10px 12px; pointer-events: none; }
.hud > * { pointer-events: auto; }
.top { top: var(--safe-t); align-items: flex-start; }
.left-c, .right-c { display: flex; gap: 8px; align-items: center; }
.btn.icon { padding: 8px 12px; font-size: 16px; border-radius: 12px; }
.btn.icon.on { border-color: rgba(53, 224, 255, 0.6); box-shadow: 0 0 12px rgba(53, 224, 255, 0.25); }
.chip.code { cursor: pointer; font-family: ui-monospace, monospace; font-weight: 700; color: var(--cyan); }

/* 座位牌 */
.plate {
  position: absolute; z-index: 5; top: calc(64px + var(--safe-t));
  display: flex; align-items: center; gap: 10px; padding: 9px 13px; border-radius: 16px;
  max-width: 44vw;
}
.plate.left { left: 12px; }
.plate.right { right: 12px; flex-direction: row-reverse; }
.plate.right .bubble { right: 8px; left: auto; }
.pav { position: relative; font-size: 30px; line-height: 1; border-radius: 50%; padding: 5px; }
.pav.turn { box-shadow: 0 0 0 3px var(--gold), 0 0 22px rgba(245, 193, 69, 0.55); animation: pulse-glow 1.2s infinite; }
.pav.big { font-size: 34px; }
.crown { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); font-size: 15px; font-style: normal; }
.pname { font-weight: 700; font-size: 13.5px; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pmeta { font-size: 11.5px; color: var(--text-1); margin-top: 2px; }
.gold { color: var(--gold); }
.pright { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.cards-left { font-size: 13px; font-weight: 800; color: var(--cyan); }
.okay { color: var(--green); font-size: 12px; }
.cd {
  min-width: 26px; height: 26px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: rgba(255, 92, 108, 0.18); border: 1px solid rgba(255, 92, 108, 0.55);
  color: #ffb9c1; font-weight: 800; font-size: 13px;
}
.cd.big { min-width: 34px; height: 34px; font-size: 16px; }
.pempty { color: #5c6b93; font-size: 13px; padding: 4px 8px; }

.bubble {
  position: absolute; top: calc(100% + 8px); left: 8px; z-index: 6;
  background: rgba(12, 18, 38, 0.95); border: 1px solid var(--line);
  padding: 7px 14px; border-radius: 14px; font-size: 14px; font-weight: 700;
  white-space: nowrap; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}
.bubble.mine { position: absolute; left: 50%; transform: translateX(-50%); bottom: 34vh; top: auto; z-index: 6; }

/* 等待面板 */
.waitbox {
  position: absolute; z-index: 6; left: 50%; top: 46%; transform: translate(-50%, -50%);
  padding: 26px 30px; text-align: center; width: min(430px, 92vw);
}
.waitbox h2 { font-size: 21px; margin-bottom: 6px; }
.waitbox h2 b { font-size: 27px; letter-spacing: 3px; }
.dim { color: var(--text-1); font-size: 13px; }
.wseats { display: flex; justify-content: center; gap: 12px; margin: 18px 0; }
.wseat {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 14px 6px; border-radius: var(--r-md);
  border: 1px dashed rgba(160, 190, 255, 0.25);
}
.wseat.filled { border-style: solid; background: rgba(53, 224, 255, 0.05); }
.wav { font-size: 30px; }
.wname { font-size: 12.5px; font-weight: 600; max-width: 90px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip.ok { color: var(--green); border-color: rgba(61, 220, 151, 0.4); }
.wbtns { display: flex; gap: 10px; justify-content: center; }
.big { font-size: 16px; padding: 13px 28px; }

/* 底部 */
.bottom {
  bottom: 0; flex-direction: column; align-items: center; gap: 8px;
  padding-bottom: calc(10px + var(--safe-b));
}
.my-plate {
  position: absolute; left: 12px; bottom: calc(12px + var(--safe-b));
  display: flex; align-items: center; gap: 10px;
}
.actions { display: flex; gap: 10px; margin-bottom: 25vh; }
.act { font-size: 15.5px; padding: 12px 24px; border-radius: 14px; }
.dim-hint { color: var(--text-1); font-size: 13.5px; margin-bottom: 25vh; background: rgba(10,16,34,0.55); padding: 8px 18px; border-radius: 999px; }
.chatbar { position: absolute; right: 10px; bottom: calc(14px + var(--safe-b)); display: flex; flex-direction: column; gap: 6px; }
.chatchip {
  border: 1px solid var(--line); background: rgba(12, 18, 38, 0.8); color: var(--text-0);
  border-radius: 999px; padding: 6px 10px; font-size: 13px; cursor: pointer;
}

/* 结算 */
.modal-mask {
  position: absolute; inset: 0; z-index: 20; display: flex; align-items: center; justify-content: center;
  background: rgba(4, 6, 14, 0.65); backdrop-filter: blur(4px);
}
.settle { width: min(420px, 92vw); padding: 26px; text-align: center; }
.settle h2 { font-size: 32px; margin-bottom: 12px; }
.winh { color: var(--gold); text-shadow: 0 0 30px rgba(245, 193, 69, 0.5); }
.loseh { color: #93a3c9; }
.badges { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-bottom: 16px; }
.chip.spring { color: var(--pink); border-color: rgba(255, 107, 157, 0.45); }
.srows { display: flex; flex-direction: column; gap: 6px; margin-bottom: 18px; }
.srow {
  display: flex; align-items: center; gap: 10px; padding: 9px 14px;
  background: rgba(10, 16, 34, 0.5); border-radius: var(--r-md);
}
.srow.meRow { border: 1px solid rgba(245, 193, 69, 0.35); }
.sname { flex: 1; text-align: left; font-size: 14px; font-weight: 600; }
.sdelta { font-weight: 800; font-family: ui-monospace, monospace; }
.sdelta.up { color: var(--green); }
.sdelta.down { color: var(--red); }
.sbtns { display: flex; gap: 10px; justify-content: center; }

/* 手机竖屏微调 */
@media (max-aspect-ratio: 1/1) {
  .plate { top: calc(56px + var(--safe-t)); padding: 7px 10px; }
  .pav { font-size: 24px; }
  .pname { max-width: 72px; font-size: 12px; }
  .pmeta { display: none; }
  .actions { margin-bottom: 34vh; flex-wrap: wrap; justify-content: center; }
  .dim-hint { margin-bottom: 34vh; }
  .my-plate .pinfo { display: none; }
  .chatbar { bottom: auto; top: 40%; }
  .bubble.mine { bottom: 44vh; }
}
</style>
