/* 麻将牌面纹理:Canvas 程序化生成万/筒/条,零外部资源。
   kind:0-8 万1-9,9-17 筒1-9,18-26 条1-9。tile id = kind*4+copy。
   工艺风格:象牙面微光泽 + 传统铜钱纹筒子 + 竹节条子 + 手绘幺鸡。 */
import * as THREE from 'three'

const W = 256
const H = 342
const RED = '#c02f2f'
const RED_DEEP = '#8e1f1f'
const GREEN = '#1e7d4c'
const GREEN_DEEP = '#14573a'
const BLUE = '#2c4a88'
const INK = '#23232b'
const CN = ['一', '二', '三', '四', '五', '六', '七', '八', '九']
const KAI = '"Kaiti SC", "STKaiti", "KaiTi", serif'

const cache = new Map()

export const kindOf = (tile) => Math.floor(tile / 4)
export const suitOf = (kind) => Math.floor(kind / 9)
export const kindLabel = (kind) => `${kind % 9 + 1}${['万', '筒', '条'][suitOf(kind)]}`

function base() {
  const c = document.createElement('canvas')
  c.width = W
  c.height = H
  const g = c.getContext('2d')
  // 象牙底:纵向渐变 + 左上柔光,四边内阴影营造倒角
  const grad = g.createLinearGradient(0, 0, 0, H)
  grad.addColorStop(0, '#fdfaf0')
  grad.addColorStop(0.5, '#f7f0dd')
  grad.addColorStop(1, '#ece1c6')
  g.fillStyle = grad
  g.beginPath()
  g.roundRect(4, 4, W - 8, H - 8, 26)
  g.fill()
  const sheen = g.createRadialGradient(W * 0.3, H * 0.2, 10, W * 0.3, H * 0.2, W * 0.9)
  sheen.addColorStop(0, 'rgba(255,255,255,0.5)')
  sheen.addColorStop(0.5, 'rgba(255,255,255,0)')
  g.fillStyle = sheen
  g.beginPath()
  g.roundRect(4, 4, W - 8, H - 8, 26)
  g.fill()
  // 内侧倒角:上亮下暗
  g.lineWidth = 5
  g.strokeStyle = 'rgba(120, 95, 45, 0.20)'
  g.beginPath()
  g.roundRect(6, 6, W - 12, H - 12, 24)
  g.stroke()
  g.lineWidth = 2
  g.strokeStyle = 'rgba(255,255,255,0.8)'
  g.beginPath()
  g.roundRect(10, 10, W - 20, H - 20, 21)
  g.stroke()
  return [c, g]
}

/* n 个元素的经典阵列坐标(相对 0-1) */
function layout(n) {
  const L = {
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
  // 数字:朱红书法,带浅影
  g.font = `900 128px ${KAI}`
  g.shadowColor = 'rgba(142, 31, 31, 0.35)'
  g.shadowBlur = 0
  g.shadowOffsetY = 4
  g.fillStyle = RED
  g.fillText(CN[n - 1], W / 2, H * 0.3)
  // 萬:墨色,先画高光再画本体,做出微浮雕
  g.shadowColor = 'transparent'
  g.font = `900 118px ${KAI}`
  g.fillStyle = 'rgba(255,255,255,0.75)'
  g.fillText('萬', W / 2 - 2, H * 0.72 - 3)
  g.fillStyle = INK
  g.fillText('萬', W / 2, H * 0.72)
}

/* 铜钱纹筒:外环 + 花瓣圈 + 渐变实心 */
function coin(g, cx, cy, r, fill) {
  g.lineWidth = Math.max(4, r * 0.16)
  g.strokeStyle = BLUE
  g.beginPath()
  g.arc(cx, cy, r, 0, Math.PI * 2)
  g.stroke()
  // 花瓣圈
  const petals = r > 40 ? 12 : 8
  g.lineWidth = Math.max(2, r * 0.07)
  g.strokeStyle = fill === RED ? RED_DEEP : GREEN_DEEP
  for (let i = 0; i < petals; i++) {
    const a = (i / petals) * Math.PI * 2
    const pr = r * 0.68
    g.beginPath()
    g.arc(cx + Math.cos(a) * pr, cy + Math.sin(a) * pr, r * 0.16, a + Math.PI * 0.5, a + Math.PI * 1.5)
    g.stroke()
  }
  // 内芯:径向渐变 + 高光点
  const core = g.createRadialGradient(cx - r * 0.15, cy - r * 0.18, r * 0.05, cx, cy, r * 0.46)
  core.addColorStop(0, fill === RED ? '#e05b52' : '#37a06b')
  core.addColorStop(1, fill === RED ? RED_DEEP : GREEN_DEEP)
  g.fillStyle = core
  g.beginPath()
  g.arc(cx, cy, r * 0.44, 0, Math.PI * 2)
  g.fill()
  g.fillStyle = 'rgba(255,255,255,0.55)'
  g.beginPath()
  g.arc(cx - r * 0.16, cy - r * 0.18, r * 0.1, 0, Math.PI * 2)
  g.fill()
}

function drawTong(g, n) {
  if (n === 1) {
    // 大饼:双环大铜钱
    coin(g, W / 2, H / 2, 92, RED)
    g.lineWidth = 5
    g.strokeStyle = 'rgba(44, 74, 136, 0.4)'
    g.beginPath()
    g.arc(W / 2, H / 2, 108, 0, Math.PI * 2)
    g.stroke()
    return
  }
  const pts = layout(n)
  const r = n <= 4 ? 42 : 30
  pts.forEach(([x, y], i) => coin(g, x * W, y * H, r, i % 2 === 0 ? RED : GREEN))
}

/* 竹节:渐变圆棒 + 竹节环 */
function bamboo(g, cx, cy, bw, bh, color) {
  const grad = g.createLinearGradient(cx - bw / 2, 0, cx + bw / 2, 0)
  const [lite, dark] = color === RED ? ['#e05b52', RED_DEEP] : ['#37a06b', GREEN_DEEP]
  grad.addColorStop(0, dark)
  grad.addColorStop(0.35, lite)
  grad.addColorStop(0.65, lite)
  grad.addColorStop(1, dark)
  g.fillStyle = grad
  g.beginPath()
  g.roundRect(cx - bw / 2, cy - bh / 2, bw, bh, bw / 2)
  g.fill()
  // 两道竹节环
  g.strokeStyle = 'rgba(255,255,255,0.7)'
  g.lineWidth = 3
  for (const t of [0.32, 0.68]) {
    g.beginPath()
    g.moveTo(cx - bw / 2 + 2, cy - bh / 2 + bh * t)
    g.lineTo(cx + bw / 2 - 2, cy - bh / 2 + bh * t)
    g.stroke()
  }
}

/* 幺鸡:手绘竹雀,跨平台一致(不依赖 emoji) */
function drawBird(g) {
  const cx = W / 2
  const cy = H / 2
  g.save()
  g.translate(cx, cy)
  // 尾羽三根
  g.lineWidth = 10
  g.lineCap = 'round'
  for (const [a, color] of [[-0.5, BLUE], [-0.2, RED], [0.1, GREEN_DEEP]]) {
    g.strokeStyle = color
    g.beginPath()
    g.moveTo(-14, 26)
    g.quadraticCurveTo(-52 * Math.cos(a) - 20, 60 * Math.sin(a) + 44, -66 - a * 22, 66 + a * 40)
    g.stroke()
  }
  // 身体
  const body = g.createLinearGradient(0, -60, 0, 60)
  body.addColorStop(0, '#37a06b')
  body.addColorStop(1, GREEN_DEEP)
  g.fillStyle = body
  g.beginPath()
  g.moveTo(-16, -52)
  g.bezierCurveTo(34, -66, 44, -6, 22, 36)
  g.bezierCurveTo(12, 56, -20, 58, -26, 34)
  g.bezierCurveTo(-34, 6, -36, -40, -16, -52)
  g.fill()
  // 翅膀
  g.fillStyle = RED
  g.beginPath()
  g.moveTo(-8, -12)
  g.bezierCurveTo(20, -22, 26, 8, 4, 26)
  g.bezierCurveTo(-10, 34, -20, 12, -8, -12)
  g.fill()
  // 头与喙
  g.fillStyle = '#37a06b'
  g.beginPath()
  g.arc(14, -54, 20, 0, Math.PI * 2)
  g.fill()
  g.fillStyle = '#e8a020'
  g.beginPath()
  g.moveTo(30, -58)
  g.lineTo(52, -50)
  g.lineTo(30, -44)
  g.closePath()
  g.fill()
  // 眼睛 + 头冠
  g.fillStyle = '#fff'
  g.beginPath(); g.arc(18, -57, 6, 0, Math.PI * 2); g.fill()
  g.fillStyle = INK
  g.beginPath(); g.arc(19.5, -57, 3, 0, Math.PI * 2); g.fill()
  g.strokeStyle = RED
  g.lineWidth = 6
  g.beginPath()
  g.moveTo(6, -70)
  g.quadraticCurveTo(2, -84, -8, -86)
  g.stroke()
  // 脚爪立于竹枝
  g.strokeStyle = '#8a6a33'
  g.lineWidth = 7
  g.beginPath(); g.moveTo(-40, 70); g.lineTo(44, 62); g.stroke()
  g.strokeStyle = '#e8a020'
  g.lineWidth = 5
  g.beginPath(); g.moveTo(-2, 52); g.lineTo(-4, 66); g.stroke()
  g.beginPath(); g.moveTo(12, 50); g.lineTo(14, 64); g.stroke()
  g.restore()
}

function drawTiao(g, n) {
  if (n === 1) {
    drawBird(g)
    return
  }
  const pts = layout(n)
  const bw = n <= 4 ? 34 : 26
  const bh = n <= 4 ? 84 : 62
  pts.forEach(([x, y], i) => {
    const color = (n >= 5 && i === Math.floor(n / 2)) || (n === 7 && i === 0) ? RED : GREEN
    bamboo(g, x * W, y * H, bw, bh, color)
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
    tex.anisotropy = 8
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
    grad.addColorStop(0, '#1e8068')
    grad.addColorStop(0.5, '#15604d')
    grad.addColorStop(1, '#0c4237')
    g.fillStyle = grad
    g.beginPath()
    g.roundRect(4, 4, W - 8, H - 8, 26)
    g.fill()
    // 菱形暗纹
    g.save()
    g.clip()
    g.strokeStyle = 'rgba(255,255,255,0.05)'
    g.lineWidth = 2
    for (let i = -H; i < W + H; i += 26) {
      g.beginPath(); g.moveTo(i, 0); g.lineTo(i + H, H); g.stroke()
      g.beginPath(); g.moveTo(i + H, 0); g.lineTo(i, H); g.stroke()
    }
    // 边角暗角
    const vig = g.createRadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, H * 0.72)
    vig.addColorStop(0, 'rgba(0,0,0,0)')
    vig.addColorStop(1, 'rgba(0,0,0,0.3)')
    g.fillStyle = vig
    g.fillRect(0, 0, W, H)
    g.restore()
    // 金色内框
    g.beginPath()
    g.roundRect(14, 14, W - 28, H - 28, 18)
    g.strokeStyle = 'rgba(245, 193, 69, 0.35)'
    g.lineWidth = 3
    g.stroke()
    const tex = new THREE.CanvasTexture(c)
    tex.colorSpace = THREE.SRGBColorSpace
    cache.set('back', tex)
  }
  return cache.get('back')
}
