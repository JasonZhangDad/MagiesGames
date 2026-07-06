import { defineStore } from 'pinia'
import { socket } from '../ws'

let toastId = 0
let eventSeq = 0

export const useGameStore = defineStore('game', {
  state: () => ({
    room: null,          // 服务端快照(唯一可信源)
    events: [],          // 事件队列:必须逐条消费,不能合并(动画/音效依赖每一条)
    hintCards: null,
    toasts: [],
    connStatus: 'offline', // online | reconnecting | offline
    selected: [],        // 我选中的手牌 id
  }),
  getters: {
    mySeat: (s) => s.room?.my_seat ?? null,
    myTurn: (s) => s.room && s.room.current !== null && s.room.current === s.room.my_seat,
    phase: (s) => s.room?.phase ?? null,
  },
  actions: {
    bind() {
      socket
        .on('STATE', ({ state }) => {
          this.room = state
          if (!state) this.selected = []
        })
        .on('EVENT', ({ e }) => {
          this.events.push({ seq: ++eventSeq, ...e })
        })
        .on('ERROR', ({ msg }) => this.toast(msg, 'err'))
        .on('HINT', ({ cards }) => {
          this.hintCards = cards
          if (!cards) this.toast('没有能压过上家的牌')
        })
        .on('_status', (st) => { this.connStatus = st })
    },
    toast(text, kind = 'info') {
      const id = ++toastId
      this.toasts.push({ id, text, kind })
      setTimeout(() => { this.toasts = this.toasts.filter(t => t.id !== id) }, 2600)
    },
    send(msg) { socket.send(msg) },
    quick(game = 'ddz') { this.send({ t: 'QUICK', game }) },
    create(priv, game = 'ddz') { this.send({ t: 'CREATE', private: priv, game }) },
    join(code) { this.send({ t: 'JOIN', code }) },
    leave() { this.send({ t: 'LEAVE' }); this.selected = [] },
    ready(v = true) { this.send({ t: 'READY', ready: v }) },
    call(score) { this.send({ t: 'CALL', score }) },
    playSelected() { this.send({ t: 'PLAY', cards: [...this.selected] }) },
    pass() { this.send({ t: 'PASS' }); this.selected = [] },
    hint() { this.send({ t: 'HINT' }) },
    setAuto(on) { this.send({ t: 'AUTO', on }) },
    chat(text) { this.send({ t: 'CHAT', text }) },
    toggleSelect(card) {
      const i = this.selected.indexOf(card)
      if (i >= 0) this.selected.splice(i, 1)
      else this.selected.push(card)
    },
    // ---- 麻将 ----
    lack(suit) { this.send({ t: 'LACK', suit }) },
    discardTile(tile) { this.send({ t: 'DISCARD', tile }); this.selected = [] },
    mjClaim(action) { this.send({ t: 'MJCLAIM', action }) },
    angang(kind) { this.send({ t: 'ANGANG', kind }) },
    bugang(kind) { this.send({ t: 'BUGANG', kind }) },
    huSelf() { this.send({ t: 'HU' }) },
  },
})
