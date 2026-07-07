/* 3D 中国象棋盘:木纹棋盘(楚河汉界/九宫斜线) + 圆柱棋子 + 选子/走位提示 + 走子动画。快照全量重绘。 */
import * as THREE from 'three'
import gsap from 'gsap'

export const W = 9
export const H = 10
const S = 0.82                     // 格距
const HX = ((W - 1) / 2) * S       // x 半宽
const HZ = ((H - 1) / 2) * S       // z 半深

const PIECE_LABEL = {
  '0k': '帅', '0a': '仕', '0b': '相', '0n': '马', '0r': '车', '0c': '炮', '0p': '兵',
  '1k': '将', '1a': '士', '1b': '象', '1n': '马', '1r': '车', '1c': '炮', '1p': '卒',
}

function boardTexture() {
  const c = document.createElement('canvas')
  c.width = 920
  c.height = 1000
  const g = c.getContext('2d')
  const grad = g.createLinearGradient(0, 0, 920, 1000)
  grad.addColorStop(0, '#d9a95f')
  grad.addColorStop(0.5, '#caa254')
  grad.addColorStop(1, '#b98e45')
  g.fillStyle = grad
  g.fillRect(0, 0, 920, 1000)
  g.globalAlpha = 0.08
  for (let i = 0; i < 40; i++) {
    g.strokeStyle = '#7a5a24'
    g.lineWidth = 1 + Math.random() * 2
    g.beginPath()
    const y = Math.random() * 1000
    g.moveTo(0, y)
    g.bezierCurveTo(280, y + 20 * Math.random(), 640, y - 20 * Math.random(), 920, y)
    g.stroke()
  }
  g.globalAlpha = 1

  const m = 55
  const sx = (920 - 2 * m) / (W - 1)
  const sy = (1000 - 2 * m) / (H - 1)
  const px = (x) => m + x * sx
  const py = (y) => m + y * sy    // 纹理 y0 在上,渲染时棋盘再翻转对位
  g.strokeStyle = '#4a3312'
  g.lineWidth = 2.6
  // 横线 10 条
  for (let y = 0; y < H; y++) {
    g.beginPath(); g.moveTo(px(0), py(y)); g.lineTo(px(W - 1), py(y)); g.stroke()
  }
  // 竖线:两侧贯通,中间被楚河汉界断开
  for (let x = 0; x < W; x++) {
    if (x === 0 || x === W - 1) {
      g.beginPath(); g.moveTo(px(x), py(0)); g.lineTo(px(x), py(H - 1)); g.stroke()
    } else {
      g.beginPath(); g.moveTo(px(x), py(0)); g.lineTo(px(x), py(4)); g.stroke()
      g.beginPath(); g.moveTo(px(x), py(5)); g.lineTo(px(x), py(H - 1)); g.stroke()
    }
  }
  // 九宫斜线
  for (const [x1, y1, x2, y2] of [[3, 0, 5, 2], [5, 0, 3, 2], [3, 7, 5, 9], [5, 7, 3, 9]]) {
    g.beginPath(); g.moveTo(px(x1), py(y1)); g.lineTo(px(x2), py(y2)); g.stroke()
  }
  // 炮位/兵位十字标记
  const cross = (x, y) => {
    const d = 6, o = 4
    for (const [qx, qy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
      if ((x === 0 && qx < 0) || (x === W - 1 && qx > 0)) continue
      g.beginPath()
      g.moveTo(px(x) + qx * o, py(y) + qy * (o + d)); g.lineTo(px(x) + qx * o, py(y) + qy * o)
      g.lineTo(px(x) + qx * (o + d), py(y) + qy * o)
      g.stroke()
    }
  }
  g.lineWidth = 2
  for (const [x, y] of [[1, 2], [7, 2], [1, 7], [7, 7]]) cross(x, y)
  for (let x = 0; x < 9; x += 2) { cross(x, 3); cross(x, 6) }
  // 楚河汉界
  g.fillStyle = '#4a3312'
  g.font = `700 ${Math.floor(sy * 0.62)}px "Kaiti SC", "STKaiti", serif`
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  const ry = (py(4) + py(5)) / 2
  g.save()
  g.translate(px(1.6), ry); g.rotate(Math.PI); g.fillText('楚 河', 0, 0)
  g.restore()
  g.fillText('汉 界', px(6.4), ry)

  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = 4
  return tex
}

function pieceTexture(code) {
  const c = document.createElement('canvas')
  c.width = c.height = 256
  const g = c.getContext('2d')
  const red = code[0] === '0'
  const ink = red ? '#c22c22' : '#26221c'
  const grad = g.createRadialGradient(128, 108, 30, 128, 128, 130)
  grad.addColorStop(0, '#f7ecd2')
  grad.addColorStop(1, '#e3cda0')
  g.fillStyle = grad
  g.fillRect(0, 0, 256, 256)
  g.strokeStyle = ink
  g.lineWidth = 10
  g.beginPath(); g.arc(128, 128, 104, 0, Math.PI * 2); g.stroke()
  g.lineWidth = 3
  g.beginPath(); g.arc(128, 128, 116, 0, Math.PI * 2); g.stroke()
  g.fillStyle = ink
  g.font = '700 118px "Kaiti SC", "STKaiti", serif'
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  g.fillText(PIECE_LABEL[code], 128, 136)
  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = 4
  return tex
}

export class XiangqiScene {
  constructor(canvas, { onTapCell } = {}) {
    this.canvas = canvas
    this.onTapCell = onTapCell
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    this.scene = new THREE.Scene()
    this.camera = new THREE.PerspectiveCamera(46, 1, 0.1, 120)
    this.portrait = false
    this.flip = false              // 黑方视角时翻转棋盘

    const boardGeo = new THREE.BoxGeometry(HX * 2 + 1.15, 0.5, HZ * 2 + 1.15)
    const woodMat = new THREE.MeshStandardMaterial({ map: boardTexture(), roughness: 0.65 })
    const sideMat = new THREE.MeshStandardMaterial({ color: 0x8a6a33, roughness: 0.8 })
    this.board = new THREE.Mesh(boardGeo, [sideMat, sideMat, woodMat, sideMat, sideMat, sideMat])
    this.board.position.y = -0.25
    this.scene.add(this.board)

    this.scene.add(new THREE.HemisphereLight(0xe8f2ff, 0x2a2418, 1.15))
    const key = new THREE.DirectionalLight(0xfff2d8, 1.7)
    key.position.set(4, 14, 6)
    const cyan = new THREE.PointLight(0x35e0ff, 16, 30)
    cyan.position.set(-9, 6, -4)
    const violet = new THREE.PointLight(0x8b7bff, 14, 30)
    violet.position.set(9, 6, -4)
    this.scene.add(key, cyan, violet)

    this.pieceGeo = new THREE.CylinderGeometry(S * 0.42, S * 0.44, 0.24, 36)
    this.sideMats = {
      0: new THREE.MeshStandardMaterial({ color: 0xead7ae, roughness: 0.5 }),
      1: new THREE.MeshStandardMaterial({ color: 0xdcc494, roughness: 0.5 }),
    }
    this.topMats = new Map()       // code → 顶面材质缓存
    this.pieceGroup = new THREE.Group()
    this.fxGroup = new THREE.Group()
    this.hintGroup = new THREE.Group()
    this.scene.add(this.pieceGroup, this.fxGroup, this.hintGroup)
    this.pieces = new Map()        // "x,y" → mesh(userData.code)
    this.pendingAnim = null        // {from,to,at} 等下一次快照落地后播放

    this.markerFrom = this._ring(0xf5c145, 0.35)
    this.markerTo = this._ring(0xf5c145, 0.9)
    this.selRing = this._ring(0x3ddc97, 0.95)
    this.scene.add(this.markerFrom, this.markerTo, this.selRing)

    this.raycaster = new THREE.Raycaster()
    this.pointer = new THREE.Vector2()
    canvas.addEventListener('pointerdown', (e) => this._onTap(e))

    this._raf = 0
    this._loop()
  }

  _ring(color, opacity) {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(S * 0.46, S * 0.58, 32),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity, side: THREE.DoubleSide }),
    )
    ring.rotation.x = -Math.PI / 2
    ring.visible = false
    return ring
  }

  _topMat(code) {
    if (!this.topMats.has(code)) {
      this.topMats.set(code, new THREE.MeshStandardMaterial({ map: pieceTexture(code), roughness: 0.45 }))
    }
    return this.topMats.get(code)
  }

  setLowSpec(on) {
    this.renderer.setPixelRatio(on ? 1 : Math.min(devicePixelRatio, 2))
  }

  setFlip(flip) {
    if (this.flip === flip) return
    this.flip = flip
    this.board.rotation.y = flip ? Math.PI : 0
    for (const [key, mesh] of this.pieces) {
      const [x, y] = key.split(',').map(Number)
      mesh.position.copy(this._cellPos(x, y))
    }
  }

  _layoutCamera() {
    if (this.portrait) {
      this.camera.fov = 60
      this.camera.position.set(0, 15.6, 7.6)
      this.camera.lookAt(0, 0, -0.3)
    } else {
      this.camera.fov = 46
      this.camera.position.set(0, 12.4, 8.6)
      this.camera.lookAt(0, 0, -0.3)
    }
    this.camera.updateProjectionMatrix()
  }

  resize() {
    const w = this.canvas.clientWidth
    const h = this.canvas.clientHeight
    if (!w || !h) return
    const portrait = h > w
    if (this.canvas.width !== Math.floor(w * this.renderer.getPixelRatio()) || portrait !== this.portrait) {
      this.portrait = portrait
      this.renderer.setSize(w, h, false)
      this.camera.aspect = w / h
      this._layoutCamera()
    }
  }

  /** 引擎坐标 → 世界坐标。红方视角红在下(y0 靠近相机),黑方视角翻转。 */
  _cellPos(x, y) {
    if (this.flip) return new THREE.Vector3((4 - x) * S, 0.13, (y - 4.5) * S)
    return new THREE.Vector3((x - 4) * S, 0.13, (4.5 - y) * S)
  }

  /** 快照重绘:board[y][x] = null 或 "0r"/"1k" 等编码。 */
  setBoard(board, lastMove) {
    if (!board) { this.reset(); return }
    const want = new Set()
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const code = board[y][x]
        const key = `${x},${y}`
        if (!code) continue
        want.add(key)
        const cur = this.pieces.get(key)
        if (cur && cur.userData.code === code) continue
        if (cur) { this.pieceGroup.remove(cur); this.pieces.delete(key) }
        const mesh = new THREE.Mesh(this.pieceGeo,
          [this.sideMats[+code[0]], this._topMat(code), this.sideMats[+code[0]]])
        mesh.userData.code = code
        mesh.position.copy(this._cellPos(x, y))
        this.pieceGroup.add(mesh)
        this.pieces.set(key, mesh)
      }
    }
    for (const [key, mesh] of this.pieces) {
      if (!want.has(key)) {
        this.pieceGroup.remove(mesh)
        this.pieces.delete(key)
      }
    }
    if (lastMove) {
      this.markerFrom.visible = this.markerTo.visible = true
      this.markerFrom.position.copy(this._cellPos(lastMove.from[0], lastMove.from[1])).setY(0.02)
      this.markerTo.position.copy(this._cellPos(lastMove.to[0], lastMove.to[1])).setY(0.02)
    } else {
      this.markerFrom.visible = this.markerTo.visible = false
    }
    // 事件先于快照到达时,走子动画挂起到这里播放
    if (this.pendingAnim && Date.now() - this.pendingAnim.at < 1200) {
      const { from, to } = this.pendingAnim
      const mesh = this.pieces.get(`${to[0]},${to[1]}`)
      if (mesh) this._slide(mesh, from, to)
    }
    this.pendingAnim = null
  }

  _slide(mesh, from, to) {
    const src = this._cellPos(from[0], from[1])
    const dst = this._cellPos(to[0], to[1])
    mesh.position.copy(src)
    gsap.to(mesh.position, { x: dst.x, z: dst.z, duration: 0.28, ease: 'power2.out' })
    gsap.fromTo(mesh.position, { y: 0.7 }, { y: 0.13, duration: 0.28, ease: 'power2.in' })
  }

  animateMove(from, to) {
    const mesh = this.pieces.get(`${to[0]},${to[1]}`)
    if (mesh) this._slide(mesh, from, to)
    else this.pendingAnim = { from, to, at: Date.now() }
  }

  /** 选中棋子 + 可落点提示。sel = [x,y]|null,targets = [[x,y],...] */
  setHighlights(sel, targets = []) {
    this.selRing.visible = !!sel
    if (sel) this.selRing.position.copy(this._cellPos(sel[0], sel[1])).setY(0.03)
    while (this.hintGroup.children.length) {
      const d = this.hintGroup.children[0]
      this.hintGroup.remove(d)
    }
    for (const [x, y] of targets) {
      const dot = new THREE.Mesh(
        new THREE.CircleGeometry(S * 0.16, 20),
        new THREE.MeshBasicMaterial({ color: 0x3ddc97, transparent: true, opacity: 0.85 }),
      )
      dot.rotation.x = -Math.PI / 2
      dot.position.copy(this._cellPos(x, y)).setY(0.03)
      this.hintGroup.add(dot)
    }
  }

  celebrate(win) {
    const count = win ? 220 : 50
    const geo = new THREE.BufferGeometry()
    const pos = new Float32Array(count * 3)
    const vel = []
    for (let i = 0; i < count; i++) {
      pos.set([0, 2, 0], i * 3)
      vel.push(new THREE.Vector3((Math.random() - 0.5) * 10, 4 + Math.random() * 8, (Math.random() - 0.5) * 8))
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({
      color: win ? 0xf5c145 : 0x6b7ba8, size: 0.15,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }))
    this.scene.add(pts)
    const st = { t: 0 }
    gsap.to(st, {
      t: 1, duration: 1.7, ease: 'power1.out',
      onUpdate: () => {
        const arr = geo.attributes.position.array
        for (let i = 0; i < count; i++) {
          arr[i * 3] = vel[i].x * st.t
          arr[i * 3 + 1] = 2 + vel[i].y * st.t - 7 * st.t * st.t
          arr[i * 3 + 2] = vel[i].z * st.t
        }
        geo.attributes.position.needsUpdate = true
        pts.material.opacity = 1 - st.t
      },
      onComplete: () => { this.scene.remove(pts); geo.dispose(); pts.material.dispose() },
    })
  }

  _cellFromEvent(e) {
    const r = this.canvas.getBoundingClientRect()
    this.pointer.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1)
    this.raycaster.setFromCamera(this.pointer, this.camera)
    const hit = this.raycaster.intersectObject(this.board, false)[0]
    if (!hit) return null
    let x, y
    if (this.flip) {
      x = Math.round(4 - hit.point.x / S)
      y = Math.round(hit.point.z / S + 4.5)
    } else {
      x = Math.round(hit.point.x / S + 4)
      y = Math.round(4.5 - hit.point.z / S)
    }
    if (x < 0 || x >= W || y < 0 || y >= H) return null
    return { x, y }
  }

  _onTap(e) {
    const cell = this._cellFromEvent(e)
    if (cell) this.onTapCell?.(cell.x, cell.y)
  }

  reset() {
    for (const [, mesh] of this.pieces) this.pieceGroup.remove(mesh)
    this.pieces.clear()
    this.markerFrom.visible = this.markerTo.visible = false
    this.setHighlights(null)
    this.pendingAnim = null
    while (this.fxGroup.children.length) this.fxGroup.remove(this.fxGroup.children[0])
  }

  _loop() {
    this._raf = requestAnimationFrame(() => this._loop())
    this.resize()
    this.renderer.render(this.scene, this.camera)
  }

  dispose() {
    cancelAnimationFrame(this._raf)
    this.reset()
    this.pieceGeo.dispose()
    this.renderer.dispose()
  }
}
