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
  g.font = '900 52px Georgia, serif'
  g.textAlign = 'center'
  const word = 'JOKER'
  for (let i = 0; i < word.length; i++) {
    g.fillText(word[i], 44, 76 + i * 52)
  }
  // 中央星徽
  g.save()
  g.translate(W / 2 + 28, H / 2)
  g.font = '110px serif'
  g.textBaseline = 'middle'
  g.fillText(big ? '🌞' : '🌙', 0, 6)
  g.restore()
  g.font = 'bold 26px Georgia, serif'
  g.fillText(big ? '大王' : '小王', W / 2 + 28, H - 36)
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

  // 中央大花色/人物字
  g.textBaseline = 'middle'
  if (rank >= 11 && rank <= 13) {
    g.font = '900 150px Georgia, serif'
    g.globalAlpha = 0.92
    g.fillText(label, W / 2, H / 2 - 8)
    g.globalAlpha = 1
    g.font = '54px serif'
    g.fillText(suit, W / 2, H / 2 + 86)
  } else {
    g.font = `${rank === 14 ? 170 : 150}px serif`
    g.fillText(suit, W / 2, H / 2 + 4)
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
