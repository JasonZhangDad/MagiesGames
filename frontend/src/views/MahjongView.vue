<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { isMuted, sfx, toggleMute } from '../sounds'
import { useGameStore } from '../stores/game'
import { useUserStore } from '../stores/user'
import { MahjongScene } from '../three/mahjongScene'
import { kindLabel, kindOf, suitOf } from '../three/mahjongTiles'

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
const me = computed(() => (mySeat.value !== null && room.value) ? room.value.seats[mySeat.value] : null)
const myTurn = computed(() => room.value?.current === mySeat.value && mySeat.value !== null)
const myClaim = computed(() => room.value?.my_claim ?? null)
const myOptions = computed(() => room.value?.my_options ?? {})
const needLack = computed(() => phase.value === 'dingque' && me.value && me.value.lack === null)
const needExchange = computed(() => phase.value === 'exchange' && me.value && !me.value.exchanged)
const exchangeOk = computed(() =>
  game.selected.length === 3 && new Set(game.selected.map(t => suitOf(kindOf(t)))).size === 1)
const selected = computed(() => game.selected[0] ?? null)

const isWatcher = computed(() => !!room.value?.spectator)
// 观战时以 0 号位为视角锚点
const anchorSeat = computed(() => mySeat.value ?? 0)
const relOf = (seat) => (seat - anchorSeat.value + 4) % 4
const seatAtRel = (rel) => room.value?.seats?.[(anchorSeat.value + rel) % 4] ?? null
const seatNoAtRel = (rel) => (anchorSeat.value + rel) % 4

const countdown = computed(() => {
  if (!room.value?.deadline) return null
  return Math.max(0, Math.ceil(room.value.deadline - now.value))
})

const SUIT_NAMES = ['万', '筒', '条']
const MELD_LABEL = { peng: '碰', gang: '杠', angang: '暗杠', bugang: '杠' }

onMounted(() => {
  scene = new MahjongScene(canvasEl.value, {
    onTapTile: (tile) => {
      if (needExchange.value) {  // 换三张:多选至 3 张
        sfx.select()
        const i = game.selected.indexOf(tile)
        if (i >= 0) game.selected.splice(i, 1)
        else if (game.selected.length < 3) game.selected.push(tile)
        else return game.toast('最多选 3 张,点选中的牌可取消')
        scene.setMyHand(room.value.my_hand, null, [...game.selected])
        return
      }
      if (phase.value !== 'playing' || !myTurn.value) return
      sfx.select()
      if (selected.value === tile) {
        game.discardTile(tile)
      } else {
        game.selected = [tile]
        scene.setMyHand(room.value.my_hand, room.value.my_drawn, tile)
      }
    },
  })
  scene.setLowSpec(lowSpec.value)
  syncFromState(room.value)
  clockTimer = setInterval(() => { now.value = Date.now() / 1000 }, 250)
})

onBeforeUnmount(() => {
  clearInterval(clockTimer)
  scene?.dispose()
  scene = null
})

function syncFromState(st) {
  if (!scene || !st || st.game !== 'mahjong') return
  game.selected = game.selected.filter(t => st.my_hand?.includes(t))
  scene.setMyHand(st.my_hand || [], st.my_drawn ?? null, [...game.selected])
  const rivers = [[], [], [], []]
  st.seats?.forEach((s, i) => {
    if (s) rivers[relOf(i)] = s.discards || []
  })
  scene.setRivers(rivers)
  // 三家对手立牌(只见牌背);胡牌或未开局不显示
  const oppo = [0, 0, 0]
  if (st.phase === 'playing') {
    st.seats?.forEach((s, i) => {
      const rel = relOf(i)
      if (rel > 0 && s && !s.hu) oppo[rel - 1] = s.cards_left || 0
    })
  }
  scene.setOpponentHands(oppo)
  if (st.phase === 'settled' && st.result && !settle.value) {
    settle.value = st.result
    showSettle.value = true
  }
}

watch(room, (st) => syncFromState(st))

watch(() => game.hintCards, (cards) => {
  if (cards?.length) {
    game.selected = [cards[0]]
    scene?.setMyHand(room.value.my_hand, room.value.my_drawn, cards[0])
    game.hintCards = null
  }
})

function bubble(seat, text, ms = 2200) {
  bubbles[seat] = { text, id: Date.now() }
  setTimeout(() => {
    if (bubbles[seat] && Date.now() - bubbles[seat].id >= ms - 20) delete bubbles[seat]
  }, ms)
}

watch(() => game.events.length, () => {
  while (game.events.length) handleEvent(game.events.shift())
})

function handleEvent(e) {
  if (!e || !scene) return
  switch (e.e) {
    case 'deal':
      showSettle.value = false
      settle.value = null
      Object.keys(bubbles).forEach(k => delete bubbles[k])
      game.selected = []
      scene.reset()
      sfx.deal()
      break
    case 'exchanged':
      bubble(e.seat, '已换牌 🔄')
      sfx.click()
      break
    case 'exchange_done':
      game.toast(`🔄 换三张完成,方向:${['', '传给下家', '传给对家', '传给上家'][e.dir] ?? ''}`)
      sfx.deal()
      break
    case 'lack':
      bubble(e.seat, `定缺${SUIT_NAMES[e.suit]}`)
      sfx.click()
      break
    case 'discard':
      scene.animateDiscard(relOf(e.seat), e.tile)
      sfx.play()
      break
    case 'peng':
      bubble(e.seat, `碰!${e.label}`)
      sfx.landlord()
      break
    case 'gang':
    case 'angang':
    case 'bugang': {
      bubble(e.seat, `杠!${e.label ?? ''}`)
      if (e.pay) {
        const word = e.pay.type === 'angang' ? '下雨 🌧️' : '刮风 🌪️'
        game.toast(`💰 ${word} ${room.value?.seats?.[e.seat]?.nickname ?? ''} 杠牌收 ${e.pay.units * 100} 金币`)
      }
      sfx.bomb()
      break
    }
    case 'hu_multi': {
      e.winners.forEach((w) => {
        const s = room.value?.seats?.[w.seat]
        bubble(w.seat, w.zimo ? '自摸!' : '胡!')
        game.toast(`🎉 ${s?.nickname ?? ''} ${w.zimo ? '自摸' : '胡牌'} ${w.fan} 番(${w.names.join('/')})`)
      })
      const meWon = e.winners.some(w => w.seat === mySeat.value)
      scene.celebrate(meWon)
      meWon ? sfx.win() : sfx.landlord()
      break
    }
    case 'mj_settle':
      settle.value = e.result
      showSettle.value = true
      ;(e.result.coin_deltas[mySeat.value] ?? 0) >= 0 ? sfx.win() : sfx.lose()
      user.fetchMe()
      break
    case 'chat':
      bubble(e.seat, e.text, 3000)
      break
    case 'bot_fill':
      game.toast(`🤖 ${e.nickname} 加入补位`)
      break
    case 'auto':
      if (e.seat === mySeat.value) game.toast(e.on ? '已开启托管,AI 代打' : '已取消托管')
      break
    case 'offline': bubble(e.seat, '📴 掉线了'); break
    case 'online': bubble(e.seat, '🔌 回来了'); break
  }
}

function doExchange() {
  if (!exchangeOk.value) { game.toast('要选同一花色的 3 张牌'); return }
  game.exchange([...game.selected])
  sfx.play()
}
function doDiscard() {
  if (selected.value === null) { game.toast('先选一张牌'); return }
  game.discardTile(selected.value)
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
const quickChats = ['👍', '🔥', '😭', '碰不动了~', '血战到底!', '快点吧~']
</script>

<template>
  <div class="gamepage" v-if="room">
    <canvas ref="canvasEl" class="stage" />

    <header class="hud top">
      <div class="left-c">
        <button class="btn icon" @click="game.leave()" title="离开房间">←</button>
        <button class="chip code" @click="copyCode">🀄 {{ room.code }} ⧉</button>
        <span class="chip">血战到底 · 余 {{ room.wall_left ?? 0 }} 张</span>
        <span v-if="isWatcher" class="chip watch">👁 观战中</span>
        <span v-else-if="room.watchers" class="chip">👁 {{ room.watchers }}</span>
      </div>
      <div class="right-c">
        <button class="btn icon" @click="doMute">{{ muted ? '🔇' : '🔊' }}</button>
        <button class="btn icon" :class="{ on: lowSpec }" @click="doLowSpec">🍃</button>
        <button v-if="['playing', 'dingque', 'exchange'].includes(phase)" class="btn icon" :class="{ on: me?.auto }"
                @click="game.setAuto(!me?.auto)">🤖</button>
      </div>
    </header>

    <!-- 三个对手座位牌:rel1 右 rel2 对家 rel3 左 -->
    <div v-for="rel in [1, 2, 3]" :key="rel" class="plate glass" :class="'rel' + rel">
      <template v-if="seatAtRel(rel)">
        <div class="pav" :class="{ turn: room.current === seatNoAtRel(rel) }">
          <span>{{ seatAtRel(rel).avatar }}</span>
          <i v-if="seatAtRel(rel).hu" class="crown">🏆</i>
        </div>
        <div class="pinfo">
          <div class="pname">
            {{ seatAtRel(rel).nickname }}
            <span v-if="!seatAtRel(rel).connected">📴</span>
            <span v-else-if="seatAtRel(rel).auto">🤖</span>
          </div>
          <div class="pmeta">
            <span v-if="seatAtRel(rel).lack !== null" class="lackb">缺{{ SUIT_NAMES[seatAtRel(rel).lack] }}</span>
            <span class="cards-left">🀫{{ seatAtRel(rel).cards_left }}</span>
            <span v-for="(m, i) in seatAtRel(rel).melds" :key="i" class="meldb">
              {{ MELD_LABEL[m.type] }}{{ m.label }}
            </span>
          </div>
        </div>
        <span v-if="room.current === seatNoAtRel(rel) && countdown !== null" class="cd">{{ countdown }}</span>
        <transition name="fade">
          <div v-if="bubbles[seatNoAtRel(rel)]" class="bubble">{{ bubbles[seatNoAtRel(rel)].text }}</div>
        </transition>
      </template>
      <template v-else><div class="pempty">等待玩家…</div></template>
    </div>

    <transition name="fade">
      <div v-if="mySeat !== null && bubbles[mySeat]" class="bubble mine">{{ bubbles[mySeat].text }}</div>
    </transition>

    <!-- 等待开局 -->
    <div v-if="phase === 'waiting'" class="waitbox glass">
      <h2>麻将房 <b class="title-grad">{{ room.code }}</b></h2>
      <p class="dim">凑满 4 人开局 · 点准备后 AI 数秒内补位 · 血战到底</p>
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
        <button class="btn btn-gold big" @click="game.join(room.code)">🪑 入座对局</button>
      </div>
    </div>

    <!-- 换三张 -->
    <div v-if="needExchange && !me?.auto" class="lackbox glass">
      <h3>🔄 换三张 <span v-if="countdown !== null" class="cd">{{ countdown }}</span></h3>
      <p class="dim">点手牌选同一花色的 3 张,将随机传给下家/对家/上家</p>
      <div class="lackbtns">
        <button class="btn btn-gold lackbtn" :disabled="!exchangeOk" @click="doExchange">
          确认换牌({{ game.selected.length }}/3)
        </button>
      </div>
    </div>
    <div v-else-if="phase === 'exchange' && me?.exchanged" class="lackbox glass">
      <h3>🔄 已换牌</h3>
      <p class="dim">等待其他玩家选牌…</p>
    </div>

    <!-- 定缺 -->
    <div v-if="needLack" class="lackbox glass">
      <h3>定缺:选择你要缺的一门 <span v-if="countdown !== null" class="cd">{{ countdown }}</span></h3>
      <p class="dim">整局都不能用这门的牌胡牌,通常选手里最少的</p>
      <div class="lackbtns">
        <button v-for="(n, i) in SUIT_NAMES" :key="i" class="btn btn-cyan lackbtn" @click="game.lack(i)">
          缺{{ n }}
        </button>
      </div>
    </div>

    <footer class="hud bottom">
      <div class="my-plate" v-if="seatAtRel(0)">
        <div class="pav big" :class="{ turn: room.current === seatNoAtRel(0) }">
          <span>{{ seatAtRel(0).avatar }}</span>
          <i v-if="seatAtRel(0).hu" class="crown">🏆</i>
        </div>
        <div class="pinfo">
          <div class="pname">{{ seatAtRel(0).nickname }}<span v-if="isWatcher" class="dim"> (视角)</span></div>
          <div class="pmeta">
            <span v-if="seatAtRel(0).lack !== null" class="lackb">缺{{ SUIT_NAMES[seatAtRel(0).lack] }}</span>
            <span v-for="(m, i) in seatAtRel(0).melds" :key="i" class="meldb">{{ MELD_LABEL[m.type] }}{{ m.label }}</span>
          </div>
        </div>
        <span v-if="room.current === seatNoAtRel(0) && countdown !== null" class="cd big">{{ countdown }}</span>
      </div>

      <!-- 碰杠胡响应 -->
      <div v-if="myClaim" class="actions">
        <span class="claimtip">{{ room.seats[room.claiming?.from]?.nickname }} 打出 {{ room.claiming?.label }}</span>
        <button v-if="myClaim.includes('hu')" class="btn act btn-gold" @click="game.mjClaim('hu')">胡!</button>
        <button v-if="myClaim.includes('gang')" class="btn act btn-cyan" @click="game.mjClaim('gang')">杠</button>
        <button v-if="myClaim.includes('peng')" class="btn act btn-cyan" @click="game.mjClaim('peng')">碰</button>
        <button class="btn act" @click="game.mjClaim('pass')">过</button>
      </div>

      <!-- 我的回合 -->
      <div v-else-if="phase === 'playing' && myTurn && !me?.auto" class="actions">
        <button v-if="myOptions.hu" class="btn act btn-gold" @click="game.huSelf()">自摸胡!</button>
        <button v-for="k in myOptions.angang || []" :key="'a' + k" class="btn act btn-cyan"
                @click="game.angang(k)">暗杠{{ kindLabel(k) }}</button>
        <button v-for="k in myOptions.bugang || []" :key="'b' + k" class="btn act btn-cyan"
                @click="game.bugang(k)">补杠{{ kindLabel(k) }}</button>
        <button class="btn act" @click="game.hint()">💡 提示</button>
        <button class="btn act btn-gold" :disabled="selected === null" @click="doDiscard">
          出牌{{ selected !== null ? ' ' + kindLabel(kindOf(selected)) : '' }}
        </button>
      </div>

      <div v-else-if="['playing', 'dingque', 'exchange'].includes(phase) && me?.auto" class="actions">
        <button class="btn act btn-cyan" @click="game.setAuto(false)">🤖 托管中,点击接管</button>
      </div>

      <div v-else-if="phase === 'playing' && !myTurn && !room.claiming" class="actions dim-hint">
        等待 {{ room.seats[room.current]?.nickname ?? '' }} 出牌…
      </div>
      <div v-else-if="room.claiming && !myClaim" class="actions dim-hint">
        等待其他玩家响应 {{ room.claiming.label }}…
      </div>

      <div class="chatbar" v-if="phase !== 'waiting' && !isWatcher">
        <button v-for="c in quickChats" :key="c" class="chatchip" @click="game.chat(c)">{{ c }}</button>
      </div>
    </footer>

    <!-- 结算 -->
    <transition name="fade">
      <div v-if="showSettle && settle" class="modal-mask">
        <div class="settle glass">
          <h2 :class="(settle.coin_deltas[mySeat] ?? 0) >= 0 ? 'winh' : 'loseh'">
            {{ settle.draw && !settle.winners.length ? '🌫️ 荒庄流局'
              : (settle.coin_deltas[mySeat] ?? 0) >= 0 ? '🏆 胜利!' : '💔 惜败' }}
          </h2>
          <div v-if="settle.winners.length" class="wlist">
            <div v-for="(w, i) in settle.winners" :key="i" class="wrow">
              <span class="wav">{{ room.seats[w.seat]?.avatar }}</span>
              <span class="sname">{{ room.seats[w.seat]?.nickname }}</span>
              <span class="chip">{{ w.zimo ? '自摸' : `接炮·${room.seats[w.from_seat]?.nickname}` }}</span>
              <span class="chip gold">{{ w.fan }} 番 · {{ w.names.join(' ') }}</span>
            </div>
          </div>
          <div class="srows">
            <div v-for="(s, i) in room.seats" :key="i" class="srow" :class="{ meRow: i === mySeat }">
              <span class="wav">{{ s?.avatar }}</span>
              <span class="sname">{{ s?.nickname }}</span>
              <span class="sdelta" :class="(settle.coin_deltas[i] ?? 0) >= 0 ? 'up' : 'down'">
                {{ (settle.coin_deltas[i] ?? 0) >= 0 ? '+' : '' }}{{ (settle.coin_deltas[i] ?? 0).toLocaleString() }}
              </span>
            </div>
          </div>
          <div class="sbtns">
            <template v-if="!isWatcher">
              <button v-if="!me?.ready" class="btn btn-gold big" @click="game.ready(true)">🔄 再来一局</button>
              <button v-else class="btn" disabled>等待其他玩家…</button>
            </template>
            <button v-else class="btn btn-gold" @click="showSettle = false">继续观战</button>
            <button class="btn btn-ghost" @click="game.leave()">返回大厅</button>
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
.chip.watch { color: var(--violet, #8b7bff); border-color: rgba(139, 123, 255, 0.45); }

.plate {
  position: absolute; z-index: 5; display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: 16px; max-width: 46vw;
}
.plate.rel1 { right: 12px; top: 38%; flex-direction: row-reverse; }
.plate.rel2 { left: 50%; transform: translateX(-50%); top: calc(56px + var(--safe-t)); }
.plate.rel3 { left: 12px; top: 38%; }
.plate.rel1 .bubble { right: 8px; left: auto; }
.pav { position: relative; font-size: 28px; line-height: 1; border-radius: 50%; padding: 5px; }
.pav.turn { box-shadow: 0 0 0 3px var(--gold), 0 0 22px rgba(245, 193, 69, 0.55); }
.pav.big { font-size: 34px; }
.crown { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); font-size: 14px; font-style: normal; }
.pname { font-weight: 700; font-size: 13px; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pmeta { display: flex; flex-wrap: wrap; gap: 4px; font-size: 11px; color: var(--text-1); margin-top: 3px; }
.cards-left { color: var(--cyan); font-weight: 800; }
.lackb { color: var(--pink); border: 1px solid rgba(255, 107, 157, 0.4); border-radius: 6px; padding: 0 5px; }
.meldb { color: var(--gold); border: 1px solid rgba(245, 193, 69, 0.35); border-radius: 6px; padding: 0 5px; }
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
.bubble.mine { left: 50%; transform: translateX(-50%); bottom: 32vh; top: auto; }

.waitbox, .lackbox {
  position: absolute; z-index: 6; left: 50%; top: 44%; transform: translate(-50%, -50%);
  padding: 24px 28px; text-align: center; width: min(460px, 92vw);
}
.waitbox h2 { font-size: 21px; margin-bottom: 6px; }
.waitbox h2 b { font-size: 27px; letter-spacing: 3px; }
.dim { color: var(--text-1); font-size: 13px; }
.wseats { display: flex; justify-content: center; gap: 8px; margin: 16px 0; flex-wrap: wrap; }
.wseat {
  flex: 1; min-width: 88px; display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 12px 4px; border-radius: var(--r-md); border: 1px dashed rgba(160, 190, 255, 0.25);
}
.wseat.filled { border-style: solid; background: rgba(53, 224, 255, 0.05); }
.wav { font-size: 28px; }
.wname { font-size: 12px; font-weight: 600; max-width: 84px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip.ok { color: var(--green); border-color: rgba(61, 220, 151, 0.4); }
.chip.gold { color: var(--gold); border-color: rgba(245, 193, 69, 0.4); }
.wbtns { display: flex; gap: 10px; justify-content: center; }
.big { font-size: 16px; padding: 13px 28px; }

.lackbox h3 { font-size: 17px; margin-bottom: 6px; display: flex; align-items: center; justify-content: center; gap: 10px; }
.lackbtns { display: flex; gap: 12px; justify-content: center; margin-top: 16px; }
.lackbtn { font-size: 17px; padding: 14px 26px; }

.bottom { bottom: 0; flex-direction: column; align-items: center; gap: 8px; padding-bottom: calc(10px + var(--safe-b)); }
.my-plate { position: absolute; left: 12px; bottom: calc(12px + var(--safe-b)); display: flex; align-items: center; gap: 10px; max-width: 46vw; }
.actions { display: flex; gap: 10px; margin-bottom: 24vh; flex-wrap: wrap; justify-content: center; align-items: center; }
.act { font-size: 15px; padding: 11px 20px; border-radius: 14px; }
.claimtip { color: var(--gold); font-size: 14px; font-weight: 600; background: rgba(10,16,34,0.7); padding: 8px 14px; border-radius: 999px; }
.dim-hint { color: var(--text-1); font-size: 13.5px; margin-bottom: 24vh; background: rgba(10,16,34,0.55); padding: 8px 18px; border-radius: 999px; }
.chatbar { position: absolute; right: 10px; bottom: calc(14px + var(--safe-b)); display: flex; flex-direction: column; gap: 6px; }
.chatchip {
  border: 1px solid var(--line); background: rgba(12, 18, 38, 0.8); color: var(--text-0);
  border-radius: 999px; padding: 6px 10px; font-size: 12.5px; cursor: pointer;
}

.modal-mask {
  position: absolute; inset: 0; z-index: 20; display: flex; align-items: center; justify-content: center;
  background: rgba(4, 6, 14, 0.65); backdrop-filter: blur(4px);
}
.settle { width: min(460px, 94vw); padding: 24px; text-align: center; max-height: 86vh; overflow-y: auto; }
.settle h2 { font-size: 30px; margin-bottom: 12px; }
.winh { color: var(--gold); text-shadow: 0 0 30px rgba(245, 193, 69, 0.5); }
.loseh { color: #93a3c9; }
.wlist { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.wrow {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; flex-wrap: wrap;
  background: rgba(245, 193, 69, 0.07); border: 1px solid rgba(245, 193, 69, 0.25); border-radius: var(--r-md);
}
.srows { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.srow { display: flex; align-items: center; gap: 10px; padding: 8px 14px; background: rgba(10, 16, 34, 0.5); border-radius: var(--r-md); }
.srow.meRow { border: 1px solid rgba(245, 193, 69, 0.35); }
.sname { flex: 1; text-align: left; font-size: 14px; font-weight: 600; }
.sdelta { font-weight: 800; font-family: ui-monospace, monospace; }
.sdelta.up { color: var(--green); }
.sdelta.down { color: var(--red); }
.sbtns { display: flex; gap: 10px; justify-content: center; }

@media (max-aspect-ratio: 1/1) {
  .plate { padding: 6px 9px; }
  .plate.rel1, .plate.rel3 { top: 30%; }
  .pav { font-size: 22px; }
  .pname { max-width: 64px; font-size: 11.5px; }
  .actions { margin-bottom: 30vh; }
  .dim-hint { margin-bottom: 30vh; }
  .my-plate .pinfo { max-width: 30vw; }
  .chatbar { bottom: auto; top: 42%; }
  .bubble.mine { bottom: 40vh; }
}
</style>
