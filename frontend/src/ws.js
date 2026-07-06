/* WebSocket 客户端:自动重连 + 心跳,消息分发给回调。 */
export class GameSocket {
  constructor() {
    this.ws = null
    this.handlers = {}
    this.retry = 0
    this.alive = false
    this.closedByUser = false
    this._hb = null
  }

  on(type, fn) { this.handlers[type] = fn; return this }

  connect(token) {
    this.token = token
    this.closedByUser = false
    this._open()
  }

  _open() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(this.token)}`)
    this.ws = ws
    ws.onopen = () => {
      this.retry = 0
      this.alive = true
      this.handlers._status?.('online')
      clearInterval(this._hb)
      this._hb = setInterval(() => this.send({ t: 'PING' }), 25000)
    }
    ws.onmessage = (ev) => {
      let msg
      try { msg = JSON.parse(ev.data) } catch { return }
      this.handlers[msg.t]?.(msg)
    }
    ws.onclose = (ev) => {
      this.alive = false
      clearInterval(this._hb)
      if (this.closedByUser || ev.code === 4401 || ev.code === 4000) return
      this.handlers._status?.('reconnecting')
      const delay = Math.min(8000, 800 * 2 ** this.retry++)
      setTimeout(() => { if (!this.closedByUser) this._open() }, delay)
    }
    ws.onerror = () => ws.close()
  }

  send(msg) {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(msg))
  }

  close() {
    this.closedByUser = true
    clearInterval(this._hb)
    this.ws?.close()
  }
}

export const socket = new GameSocket()
