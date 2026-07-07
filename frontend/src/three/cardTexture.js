/* Canvas 程序化生成扑克牌纹理:牌面 54 张 + 牌背,零外部资源。 */
import * as THREE from 'three'

const W = 256
const H = 358
const SUITS = ['♠', '♥', '♣', '♦']
const SUIT_RED = [false, true, false, true]
const RED = '#e23b4e'
const BLACK = '#232a4d'
const RANK_LABEL = { 11: 'J', 12: 'Q', 13: 'K', 14: 'A', 15: '2' }

const cache = new Map()

function roundRect(g, x, y, w, h, r) {
  g.beginPath()
  g.moveTo(x + r, y)
  g.arcTo(x + w, y, x + w, y + h, r)
  g.arcTo(x + w, y + h, x, y + h, r)
  g.arcTo(x, y + h, x, y, r)
  g.arcTo(x, y, x + w, y, r)
  g.closePath()
}

function baseCanvas() {
  const c = document.createElement('canvas')
  c.width = W
  c.height = H
  const g = c.getContext('2d')
  // 牌面底:微渐变象牙白 + 细边
  const grad = g.createLinearGradient(0, 0, W, H)
  grad.addColorStop(0, '#ffffff')
  grad.addColorStop(1, '#eef0f8')
  roundRect(g, 4, 4, W - 8, H - 8, 26)
  g.fillStyle = grad
  g.fill()
  g.lineWidth = 3
  g.strokeStyle = 'rgba(35, 42, 77, 0.16)'
  g.stroke()
  return [c, g]
}

function rankOf(id) { return Math.floor(id / 4) + 3 }
function labelOf(rank) { return RANK_LABEL[rank] || String(rank) }

function drawJoker(g, big) {
  const color = big ? RED : BLACK
  g.fillStyle = color
  g.font = '900 46px Georgia, serif'
  g.textAlign = 'center'
  const word = 'JOKER'
  for (let i = 0; i < word.length; i++) {
    g.fillText(word[i], 40, 72 + i * 48)
  }
  // 中央徽记:大王手绘骄阳,小王手绘弯月(不依赖 emoji,跨平台一致)
  const cx = W / 2 + 26
  const cy = H / 2 - 6
  if (big) {
    g.save()
    g.translate(cx, cy)
    const glow = g.createRadialGradient(0, 0, 6, 0, 0, 62)
    glow.addColorStop(0, '#ffdf7e')
    glow.addColorStop(1, 'rgba(255, 190, 60, 0)')
    g.fillStyle = glow
    g.beginPath(); g.arc(0, 0, 62, 0, Math.PI * 2); g.fill()
    g.fillStyle = '#f5a623'
    for (let i = 0; i < 12; i++) {
      g.save()
      g.rotate((i / 12) * Math.PI * 2)
      g.beginPath()
      g.moveTo(0, -34); g.lineTo(7, -52); g.lineTo(-7, -52)
      g.closePath(); g.fill()
      g.restore()
    }
    const core = g.createRadialGradient(-8, -10, 4, 0, 0, 34)
    core.addColorStop(0, '#ffe9a8')
    core.addColorStop(1, '#f08c00')
    g.fillStyle = core
    g.beginPath(); g.arc(0, 0, 33, 0, Math.PI * 2); g.fill()
    g.restore()
  } else {
    g.save()
    g.translate(cx, cy)
    const glow = g.createRadialGradient(0, 0, 8, 0, 0, 58)
    glow.addColorStop(0, 'rgba(160, 190, 255, 0.5)')
    glow.addColorStop(1, 'rgba(160, 190, 255, 0)')
    g.fillStyle = glow
    g.beginPath(); g.arc(0, 0, 58, 0, Math.PI * 2); g.fill()
    const moon = g.createLinearGradient(-30, -30, 24, 30)
    moon.addColorStop(0, '#dfe8ff')
    moon.addColorStop(1, '#8fa3d8')
    g.fillStyle = moon
    g.beginPath()
    g.arc(0, 0, 36, Math.PI * 0.32, Math.PI * 1.68)
    g.arc(16, 0, 30, Math.PI * 1.6, Math.PI * 0.4, true)
    g.closePath()
    g.fill()
    // 三颗小星
    g.fillStyle = '#dfe8ff'
    for (const [sx, sy, r] of [[26, -30, 3.4], [38, -12, 2.4], [30, 26, 2.8]]) {
      g.beginPath(); g.arc(sx, sy, r, 0, Math.PI * 2); g.fill()
    }
    g.restore()
  }
  g.fillStyle = color
  g.font = 'bold 28px Georgia, serif'
  g.fillText(big ? '大王' : '小王', cx, H - 34)
}

/* 标准扑克点阵坐标(相对 0-1,下半区自动倒置) */
const PIPS = {
  1: [[0.5, 0.5]],
  2: [[0.5, 0.22], [0.5, 0.78]],
  3: [[0.5, 0.22], [0.5, 0.5], [0.5, 0.78]],
  4: [[0.33, 0.22], [0.67, 0.22], [0.33, 0.78], [0.67, 0.78]],
  5: [[0.33, 0.22], [0.67, 0.22], [0.5, 0.5], [0.33, 0.78], [0.67, 0.78]],
  6: [[0.33, 0.22], [0.67, 0.22], [0.33, 0.5], [0.67, 0.5], [0.33, 0.78], [0.67, 0.78]],
  7: [[0.33, 0.22], [0.67, 0.22], [0.5, 0.36], [0.33, 0.5], [0.67, 0.5], [0.33, 0.78], [0.67, 0.78]],
  8: [[0.33, 0.22], [0.67, 0.22], [0.5, 0.36], [0.33, 0.5], [0.67, 0.5], [0.5, 0.64], [0.33, 0.78], [0.67, 0.78]],
  9: [[0.33, 0.2], [0.67, 0.2], [0.33, 0.4], [0.67, 0.4], [0.5, 0.5], [0.33, 0.6], [0.67, 0.6], [0.33, 0.8], [0.67, 0.8]],
  10: [[0.33, 0.2], [0.67, 0.2], [0.5, 0.3], [0.33, 0.4], [0.67, 0.4], [0.33, 0.6], [0.67, 0.6], [0.5, 0.7], [0.33, 0.8], [0.67, 0.8]],
}

function drawFace(id) {
  const [c, g] = baseCanvas()
  if (id >= 52) {
    drawJoker(g, id === 53)
    return c
  }
  const rank = rankOf(id)
  const suit = SUITS[id % 4]
  const color = SUIT_RED[id % 4] ? RED : BLACK
  const label = labelOf(rank)
  g.fillStyle = color

  // 左上/右下角标
  g.textAlign = 'center'
  const drawCorner = (x, y, flip) => {
    g.save()
    g.translate(x, y)
    if (flip) g.rotate(Math.PI)
    g.font = '800 64px "Arial Narrow", Arial, sans-serif'
    g.fillText(label, 0, 0)
    g.font = '44px serif'
    g.fillText(suit, 0, 44)
    g.restore()
  }
  drawCorner(40, 68, false)
  drawCorner(W - 40, H - 68, true)

  // 中央:人物牌饰框大字,A 独立大花色,数字牌标准点阵
  g.textBaseline = 'middle'
  if (rank >= 11 && rank <= 13) {
    // 饰框
    roundRect(g, 62, 82, W - 124, H - 164, 14)
    g.lineWidth = 3
    g.strokeStyle = color
    g.stroke()
    roundRect(g, 70, 90, W - 140, H - 180, 10)
    g.lineWidth = 1.5
    g.globalAlpha = 0.5
    g.stroke()
    g.globalAlpha = 1
    g.font = '900 128px Georgia, serif'
    g.fillText(label, W / 2, H / 2 - 16)
    g.font = '58px serif'
    g.fillText(suit, W / 2, H / 2 + 74)
  } else if (rank === 14) {
    g.font = '190px serif'
    g.shadowColor = SUIT_RED[id % 4] ? 'rgba(226, 59, 78, 0.35)' : 'rgba(35, 42, 77, 0.35)'
    g.shadowBlur = 22
    g.fillText(suit, W / 2, H / 2 + 4)
    g.shadowBlur = 0
  } else {
    const count = rank === 15 ? 2 : rank
    const pips = PIPS[count]
    g.font = '58px serif'
    for (const [px, py] of pips) {
      g.save()
      g.translate(px * W, py * H)
      if (py > 0.5) g.rotate(Math.PI)
      g.fillText(suit, 0, 4)
      g.restore()
    }
  }
  return c
}

function drawBack() {
  const c = document.createElement('canvas')
  c.width = W
  c.height = H
  const g = c.getContext('2d')
  roundRect(g, 4, 4, W - 8, H - 8, 26)
  const grad = g.createLinearGradient(0, 0, W, H)
  grad.addColorStop(0, '#1b2350')
  grad.addColorStop(0.55, '#2a1f66')
  grad.addColorStop(1, '#131a3e')
  g.fillStyle = grad
  g.fill()
  g.save()
  g.clip()
  // 斜纹底纹
  g.strokeStyle = 'rgba(140, 160, 255, 0.08)'
  g.lineWidth = 2
  for (let i = -H; i < W + H; i += 18) {
    g.beginPath()
    g.moveTo(i, 0)
    g.lineTo(i + H, H)
    g.stroke()
  }
  g.restore()
  // 金色双边框
  roundRect(g, 12, 12, W - 24, H - 24, 20)
  g.strokeStyle = 'rgba(245, 193, 69, 0.85)'
  g.lineWidth = 4
  g.stroke()
  roundRect(g, 22, 22, W - 44, H - 44, 14)
  g.strokeStyle = 'rgba(245, 193, 69, 0.35)'
  g.lineWidth = 2
  g.stroke()
  // 中央菱形 M 徽
  g.save()
  g.translate(W / 2, H / 2)
  g.rotate(Math.PI / 4)
  g.fillStyle = 'rgba(245, 193, 69, 0.14)'
  g.fillRect(-62, -62, 124, 124)
  g.strokeStyle = 'rgba(245, 193, 69, 0.5)'
  g.lineWidth = 3
  g.strokeRect(-62, -62, 124, 124)
  g.restore()
  g.fillStyle = '#f5c145'
  g.font = '900 96px Georgia, serif'
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  g.shadowColor = 'rgba(245, 193, 69, 0.6)'
  g.shadowBlur = 18
  g.fillText('M', W / 2, H / 2 + 4)
  return c
}

function toTexture(canvas) {
  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = 4
  return tex
}

export function faceTexture(id) {
  const key = `f${id}`
  if (!cache.has(key)) cache.set(key, toTexture(drawFace(id)))
  return cache.get(key)
}

export function backTexture() {
  if (!cache.has('back')) cache.set('back', toTexture(drawBack()))
  return cache.get('back')
}

export const CARD_RATIO = H / W
