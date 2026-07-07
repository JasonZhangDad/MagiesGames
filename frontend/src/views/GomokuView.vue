<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { createSeatRuntime, useGodotClock, useGodotSignals } from '../game/godotRuntime'
import { isMuted, sfx, toggleMute } from '../sounds'
import { useGameStore } from '../stores/game'
import { useUserStore } from '../stores/user'
import { GomokuScene } from '../three/gomokuScene'

const game = useGameStore()
const user = useUserStore()
const canvasEl = ref(null)
const muted = ref(isMuted())
const lowSpec = ref(localStorage.getItem('mg_lowspec') === '1')
const showSettle = ref(false)
const settle = ref(null)
let scene = null

const room = computed(() => game.room)
const mySeat = computed(() => room.value?.my_seat)
const phase = computed(() => room.value?.phase)
const me = computed(() => (mySeat.value !== null && room.value) ? room.value.seats[mySeat.value] : null)
const myTurn = computed(() => room.value?.current === mySeat.value && mySeat.value !== null)
const isWatcher = computed(() => !!room.value?.spectator)
const anchorSeat = computed(() => mySeat.value ?? 0)
const { seatAtRel, seatNoAtRel } = createSeatRuntime(room, anchorSeat, 2)
const oppSeat = computed(() => seatAtRel(1))
const oppSeatNo = computed(() => seatNoAtRel(1))
const blackSeat = computed(() => room.value?.first ?? 0)
const { countdown } = useGodotClock(room)
const { bubbles, bubble, clearBubbles } = useGodotSignals()

const STONE_ICON = { black: '⚫', white: '⚪' }

onMounted(() => {
  scene = new GomokuScene(canvasEl.value, {
    onTapCell: (x, y) => {
      if (phase.value !== 'playing' || !myTurn.value || me.value?.auto) return
      sfx.select()
      game.place(x, y)
    },
  })
  scene.setLowSpec(lowSpec.value)
  syncFromState(room.value, true)
})

onBeforeUnmount(() => {
  scene?.dispose()
  scene = null
})

function syncFromState(st, cold = false) {
  if (!scene || !st || st.game !== 'gomoku') return
  scene.setBoard(st.board, st.first, st.last_move, st.result?.win_line)
  scene.setHoverEnabled(st.phase === 'playing' && st.current === st.my_seat && st.my_seat !== null)
  if (cold && st.phase === 'settled' && st.result && !settle.value) {
    settle.value = st.result
    showSettle.value = true
  }
}

watch(room, (st) => syncFromState(st))

watch(() => game.hintCards, (cells) => {
  if (cells?.length === 2 && myTurn.value) {
    game.place(cells[0], cells[1])
    game.hintCards = null
  }
})

watch(() => game.events.length, () => {
  while (game.events.length) handleEvent(game.events.shift())
})

function handleEvent(e) {
  if (!e || !scene) return
  switch (e.e) {
    case 'deal':
      showSettle.value = false
      settle.value = null
      clearBubbles()
      scene.reset()
      sfx.deal()
      break
    case 'place':
      scene.animatePlace(e.x, e.y)
      sfx.play()
      break
    case 'gmk_settle': {
      settle.value = e.result
      showSettle.value = true
      const mine = isWatcher.value ? 0 : (e.result.coin_deltas[mySeat.value] ?? 0)
      scene.celebrate(mine >= 0)
      mine >= 0 ? sfx.win() : sfx.lose()
      user.fetchMe()
      break
    }
    case 'chat': bubble(e.seat, e.text, 3000); break
    case 'bot_fill': game.toast(`🤖 ${e.nickname} 加入对弈`); break
    case 'auto':
      if (e.seat === mySeat.value) game.toast(e.on ? '已开启托管,AI 代下' : '已取消托管')
      break
    case 'offline': bubble(e.seat, '📴 掉线了'); break
    case 'online': bubble(e.seat, '🔌 回来了'); break
  }
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
const quickChats = ['👍', '🔥', '😭', '好棋!', '让我想想…', '快点吧~']
const settleTitle = computed(() => {
  if (!settle.value) return ''
  if (settle.value.winner_seat === null) return '🤝 平局'
  if (isWatcher.value) return '🏁 本局结束'
  return settle.value.winner_seat === mySeat.value ? '🏆 胜利!' : '💔 惜败'
})
</script>

<template>
  <div class="gamepage godot-game godot-board-game" v-if="room">
    <canvas ref="canvasEl" class="stage" />

    <header class="hud top">
      <div class="left-c">
        <button class="btn icon" @click="game.leave()" title="离开房间">←</button>
        <button class="chip code" @click="copyCode">⚫ {{ room.code }} ⧉</button>
        <span v-if="isWatcher" class="chip watch">👁 观战中</span>
        <span v-else-if="room.watchers" class="chip">👁 {{ room.watchers }}</span>
      </div>
      <div class="right-c">
        <button class="btn icon" @click="doMute">{{ muted ? '🔇' : '🔊' }}</button>
        <button class="btn icon" :class="{ on: lowSpec }" @click="doLowSpec">🍃</button>
        <button v-if="phase === 'playing' && !isWatcher" class="btn icon" :class="{ on: me?.auto }"
                @click="game.setAuto(!me?.auto)">🤖</button>
      </div>
    </header>

    <!-- 对手座位牌 -->
    <div class="plate glass opp">
      <template v-if="oppSeat">
        <div class="pav" :class="{ turn: room.current === oppSeatNo }">
          <span>{{ oppSeat.avatar }}</span>
        </div>
        <div class="pinfo">
          <div class="pname">
            {{ STONE_ICON[oppSeat.stone] ?? '' }} {{ oppSeat.nickname }}
            <span v-if="!oppSeat.connected">📴</span>
            <span v-else-if="oppSeat.auto">🤖</span>
          </div>
          <div class="pmeta"><span class="gold">💰{{ (oppSeat.coin ?? 0).toLocaleString() }}</span></div>
        </div>
        <span v-if="room.current === oppSeatNo && countdown !== null" class="cd">{{ countdown }}</span>
        <transition name="fade">
          <div v-if="bubbles[oppSeatNo]" class="bubble">{{ bubbles[oppSeatNo].text }}</div>
        </transition>
      </template>
      <template v-else><div class="pempty">等待对手…</div></template>
    </div>

    <transition name="fade">
      <div v-if="mySeat !== null && bubbles[mySeat]" class="bubble mine">{{ bubbles[mySeat].text }}</div>
    </transition>

    <!-- 等待开局 -->
    <div v-if="phase === 'waiting'" class="waitbox glass">
      <h2>五子棋房 <b class="title-grad">{{ room.code }}</b></h2>
      <p class="dim">两人对弈 · 黑先白后 · 连五即胜 · 点准备后 AI 数秒内补位</p>
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
      <div class="wbtns" v-if="!isWatcher">
        <button v-if="!me?.ready" class="btn btn-gold big" @click="game.ready(true)">✓ 准备开局</button>
        <button v-else class="btn" @click="game.ready(false)">取消准备</button>
        <button class="btn btn-ghost" @click="copyCode">邀请好友</button>
      </div>
      <div class="wbtns" v-else>
        <button class="btn btn-gold big" @click="game.join(room.code)">🪑 入座对弈</button>
      </div>
    </div>

    <footer class="hud bottom">
      <div class="my-plate" v-if="room.seats[anchorSeat]">
        <div class="pav big" :class="{ turn: room.current === anchorSeat }">
          <span>{{ room.seats[anchorSeat].avatar }}</span>
        </div>
        <div class="pinfo">
          <div class="pname">
            {{ STONE_ICON[room.seats[anchorSeat].stone] ?? '' }} {{ room.seats[anchorSeat].nickname }}
            <span v-if="isWatcher" class="dim">(视角)</span>
          </div>
          <div class="pmeta"><span class="gold">💰{{ (room.seats[anchorSeat].coin ?? 0).toLocaleString() }}</span></div>
        </div>
        <span v-if="room.current === anchorSeat && countdown !== null" class="cd big">{{ countdown }}</span>
      </div>

      <div v-if="phase === 'playing' && myTurn && !me?.auto" class="actions turnhint">
        ✨ 轮到你落子,点击棋盘交叉点
        <button class="btn act" @click="game.hint()">💡 帮我下</button>
      </div>
      <div v-else-if="phase === 'playing' && me?.auto" class="actions">
        <button class="btn act btn-cyan" @click="game.setAuto(false)">🤖 托管中,点击接管</button>
      </div>
      <div v-else-if="phase === 'playing' && !myTurn && !isWatcher" class="actions dim-hint">
        等待 {{ room.seats[room.current]?.nickname ?? '' }} 落子…
      </div>

      <div class="chatbar" v-if="phase !== 'waiting' && !isWatcher">
        <button v-for="c in quickChats" :key="c" class="chatchip" @click="game.chat(c)">{{ c }}</button>
      </div>
    </footer>

    <!-- 结算 -->
    <transition name="fade">
      <div v-if="showSettle && settle" class="modal-mask">
        <div class="settle glass">
          <h2 :class="settleTitle.includes('胜') || settleTitle.includes('结束') || settleTitle.includes('平') ? 'winh' : 'loseh'">
            {{ settleTitle }}</h2>
          <p class="dim" style="margin-bottom:10px">共 {{ settle.moves }} 手</p>
          <div class="srows">
            <div v-for="(s, i) in room.seats" :key="i" class="srow" :class="{ meRow: i === mySeat }">
              <span class="wav">{{ s?.avatar }}</span>
              <span class="sname">{{ STONE_ICON[s?.stone] ?? '' }} {{ s?.nickname }}
                <i v-if="settle.winner_seat === i">🏆</i></span>
              <span class="sdelta" :class="(settle.coin_deltas[i] ?? 0) >= 0 ? 'up' : 'down'">
                {{ (settle.coin_deltas[i] ?? 0) >= 0 ? '+' : '' }}{{ (settle.coin_deltas[i] ?? 0).toLocaleString() }}
              </span>
            </div>
          </div>
          <div class="sbtns">
            <template v-if="!isWatcher">
              <button v-if="!me?.ready" class="btn btn-gold big" @click="game.ready(true)">🔄 再来一局</button>
              <button v-else class="btn" disabled>等待对手…</button>
            </template>
            <button v-else class="btn btn-gold" @click="showSettle = false">继续观战</button>
            <button class="btn btn-ghost" @click="game.leave()">返回大厅</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
  <div v-else class="gamepage godot-game loading"><div class="chip">正在进入房间…</div></div>
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
.chip.watch { color: #b9adff; border-color: rgba(139, 123, 255, 0.45); }
.dim { color: var(--text-1); font-size: 13px; }

.plate.opp {
  position: absolute; z-index: 5; display: flex; align-items: center; gap: 10px;
  padding: 8px 14px; border-radius: 16px; left: 50%; transform: translateX(-50%);
  top: calc(56px + var(--safe-t));
}
.pav { position: relative; font-size: 28px; line-height: 1; border-radius: 50%; padding: 5px; }
.pav.turn { box-shadow: 0 0 0 3px var(--gold), 0 0 22px rgba(245, 193, 69, 0.55); }
.pav.big { font-size: 34px; }
.pname { font-weight: 700; font-size: 13.5px; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pmeta { font-size: 11.5px; color: var(--text-1); margin-top: 3px; }
.gold { color: var(--gold); }
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
.bubble.mine { left: 50%; transform: translateX(-50%); bottom: 18vh; top: auto; }

.waitbox {
  position: absolute; z-index: 6; left: 50%; top: 44%; transform: translate(-50%, -50%);
  padding: 24px 28px; text-align: center; width: min(430px, 92vw);
}
.waitbox h2 { font-size: 21px; margin-bottom: 6px; }
.waitbox h2 b { font-size: 27px; letter-spacing: 3px; }
.wseats { display: flex; justify-content: center; gap: 10px; margin: 16px 0; }
.wseat {
  flex: 1; max-width: 150px; display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 12px 4px; border-radius: var(--r-md); border: 1px dashed rgba(160, 190, 255, 0.25);
}
.wseat.filled { border-style: solid; background: rgba(53, 224, 255, 0.05); }
.wav { font-size: 28px; }
.wname { font-size: 12px; font-weight: 600; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip.ok { color: var(--green); border-color: rgba(61, 220, 151, 0.4); }
.wbtns { display: flex; gap: 10px; justify-content: center; }
.big { font-size: 16px; padding: 13px 28px; }

.bottom { bottom: 0; flex-direction: column; align-items: center; gap: 8px; padding-bottom: calc(10px + var(--safe-b)); }
.my-plate { position: absolute; left: 12px; bottom: calc(12px + var(--safe-b)); display: flex; align-items: center; gap: 10px; max-width: 46vw; }
.actions { display: flex; gap: 10px; margin-bottom: 6vh; flex-wrap: wrap; justify-content: center; align-items: center; }
.act { font-size: 14px; padding: 9px 16px; border-radius: 14px; }
.turnhint { color: var(--gold); font-size: 14.5px; font-weight: 600; background: rgba(10,16,34,0.7); padding: 8px 16px; border-radius: 999px; }
.dim-hint { color: var(--text-1); font-size: 13.5px; margin-bottom: 6vh; background: rgba(10,16,34,0.55); padding: 8px 18px; border-radius: 999px; }
.chatbar { position: absolute; right: 10px; bottom: calc(14px + var(--safe-b)); display: flex; flex-direction: column; gap: 6px; }
.chatchip {
  border: 1px solid var(--line); background: rgba(12, 18, 38, 0.8); color: var(--text-0);
  border-radius: 999px; padding: 6px 10px; font-size: 12.5px; cursor: pointer;
}

.modal-mask {
  position: absolute; inset: 0; z-index: 20; display: flex; align-items: center; justify-content: center;
  background: rgba(4, 6, 14, 0.65); backdrop-filter: blur(4px);
}
.settle { width: min(420px, 94vw); padding: 24px; text-align: center; }
.settle h2 { font-size: 30px; margin-bottom: 6px; }
.winh { color: var(--gold); text-shadow: 0 0 30px rgba(245, 193, 69, 0.5); }
.loseh { color: #93a3c9; }
.srows { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.srow { display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: rgba(10, 16, 34, 0.5); border-radius: var(--r-md); }
.srow.meRow { border: 1px solid rgba(245, 193, 69, 0.35); }
.sname { flex: 1; text-align: left; font-size: 14px; font-weight: 600; }
.sdelta { font-weight: 800; font-family: ui-monospace, monospace; }
.sdelta.up { color: var(--green); }
.sdelta.down { color: var(--red); }
.sbtns { display: flex; gap: 10px; justify-content: center; }

@media (max-aspect-ratio: 1/1) {
  .pname { max-width: 90px; font-size: 12px; }
  .chatbar { bottom: auto; top: 34%; }
  .my-plate .pinfo { max-width: 34vw; }
}
</style>
