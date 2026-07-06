/* 麻将牌面纹理:Canvas 程序化生成万/筒/条,零外部资源。
   kind:0-8 万1-9,9-17 筒1-9,18-26 条1-9。tile id = kind*4+copy。 */
import * as THREE from 'three'

const W = 192
const H = 256
const RED = '#c23a3a'
const GREEN = '#1e7d4c'
const BLUE = '#2c4a88'
const CN = ['一', '二', '三', '四', '五', '六', '七', '八', '九']

const cache = new Map()

export const kindOf = (tile) => Math.floor(tile / 4)
export const suitOf = (kind) => Math.floor(kind / 9)
export const kindLabel = (kind) => `${kind % 9 + 1}${['万', '筒', '条'][suitOf(kind)]}`

function base() {
  const c = document.createElement('canvas')
  c.width = W
  c.height = H
  const g = c.getContext('2d')
  const grad = g.createLinearGradient(0, 0, 0, H)
  grad.addColorStop(0, '#fbf7ea')
  grad.addColorStop(1, '#efe6cf')
  g.fillStyle = grad
  g.beginPath()
  g.roundRect(3, 3, W - 6, H - 6, 20)
  g.fill()
  g.lineWidth = 3
  g.strokeStyle = 'rgba(90, 70, 30, 0.18)'
  g.stroke()
  return [c, g]
}

/* n 个元素的经典阵列坐标(相对 0-1) */
function layout(n) {
  const L = {
    1: [[0.5, 0.5]],
    2: [[0.5, 0.28], [0.5, 0.72]],
    3: [[0.28, 0.24], [0.5, 0.5], [0.72, 0.76]],
    4: [[0.3, 0.28], [0.7, 0.28], [0.3, 0.72], [0.7, 0.72]],
    5: [[0.28, 0.26], [0.72, 0.26], [0.5, 0.5], [0.28, 0.74], [0.72, 0.74]],
    6: [[0.3, 0.24], [0.7, 0.24], [0.3, 0.5], [0.7, 0.5], [0.3, 0.76], [0.7, 0.76]],
    7: [[0.26, 0.2], [0.5, 0.28], [0.74, 0.36], [0.3, 0.56], [0.7, 0.56], [0.3, 0.8], [0.7, 0.8]],
    8: [[0.3, 0.2], [0.7, 0.2], [0.3, 0.4], [0.7, 0.4], [0.3, 0.6], [0.7, 0.6], [0.3, 0.8], [0.7, 0.8]],
    9: [[0.28, 0.22], [0.5, 0.22], [0.72, 0.22], [0.28, 0.5], [0.5, 0.5], [0.72, 0.5],
        [0.28, 0.78], [0.5, 0.78], [0.72, 0.78]],
  }
  return L[n]
}

function drawWan(g, n) {
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  g.fillStyle = RED
  g.font = '900 92px "Songti SC", "STSong", serif'
  g.fillText(CN[n - 1], W / 2, H * 0.32)
  g.fillStyle = '#26262b'
  g.font = '900 84px "Songti SC", "STSong", serif'
  g.fillText('万', W / 2, H * 0.72)
}

function drawTong(g, n) {
  const pts = layout(n)
  const r = n === 1 ? 52 : n <= 4 ? 30 : 22
  pts.forEach(([x, y], i) => {
    const cx = x * W
    const cy = y * H
    g.beginPath()
    g.arc(cx, cy, r, 0, Math.PI * 2)
    g.lineWidth = Math.max(4, r * 0.22)
    g.strokeStyle = BLUE
    g.stroke()
    g.beginPath()
    g.arc(cx, cy, r * 0.45, 0, Math.PI * 2)
    g.fillStyle = i % 2 === 0 ? RED : GREEN
    g.fill()
  })
}

function drawTiao(g, n) {
  if (n === 1) {
    // 幺鸡:画一只简笔孔雀/竹节鸟
    g.textAlign = 'center'
    g.textBaseline = 'middle'
    g.font = '120px serif'
    g.fillText('🦚', W / 2, H / 2)
    return
  }
  const pts = layout(n)
  const bw = n <= 4 ? 26 : 20
  const bh = n <= 4 ? 62 : 48
  pts.forEach(([x, y], i) => {
    const cx = x * W - bw / 2
    const cy = y * H - bh / 2
    g.fillStyle = (n >= 5 && i === Math.floor(n / 2)) ? RED : GREEN
    g.beginPath()
    g.roundRect(cx, cy, bw, bh, bw / 2)
    g.fill()
    g.strokeStyle = 'rgba(255,255,255,0.55)'
    g.lineWidth = 2
    g.beginPath()
    g.moveTo(cx + 2, cy + bh / 2)
    g.lineTo(cx + bw - 2, cy + bh / 2)
    g.stroke()
  })
}

export function tileFaceTexture(kind) {
  const key = `k${kind}`
  if (!cache.has(key)) {
    const [c, g] = base()
    const n = kind % 9 + 1
    const suit = suitOf(kind)
    if (suit === 0) drawWan(g, n)
    else if (suit === 1) drawTong(g, n)
    else drawTiao(g, n)
    const tex = new THREE.CanvasTexture(c)
    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = 4
    cache.set(key, tex)
  }
  return cache.get(key)
}

export function tileBackTexture() {
  if (!cache.has('back')) {
    const c = document.createElement('canvas')
    c.width = W
    c.height = H
    const g = c.getContext('2d')
    const grad = g.createLinearGradient(0, 0, W, H)
    grad.addColorStop(0, '#1d7a63')
    grad.addColorStop(1, '#0e4a3a')
    g.fillStyle = grad
    g.beginPath()
    g.roundRect(3, 3, W - 6, H - 6, 20)
    g.fill()
    const tex = new THREE.CanvasTexture(c)
    tex.colorSpace = THREE.SRGBColorSpace
    cache.set('back', tex)
  }
  return cache.get('back')
}
