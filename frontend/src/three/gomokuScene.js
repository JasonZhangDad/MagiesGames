/* 3D 五子棋盘:木纹棋盘 + 落子动画 + 悬停预览 + 胜利连线高亮。快照全量重绘。 */
import * as THREE from 'three'
import gsap from 'gsap'

export const N = 15
const S = 0.78                 // 格距
const HALF = ((N - 1) / 2) * S

function boardTexture() {
  const c = document.createElement('canvas')
  c.width = c.height = 1024
  const g = c.getContext('2d')
  const grad = g.createLinearGradient(0, 0, 1024, 1024)
  grad.addColorStop(0, '#d9a95f')
  grad.addColorStop(0.5, '#caa254')
  grad.addColorStop(1, '#b98e45')
  g.fillStyle = grad
  g.fillRect(0, 0, 1024, 1024)
  // 木纹
  g.globalAlpha = 0.08
  for (let i = 0; i < 40; i++) {
    g.strokeStyle = '#7a5a24'
    g.lineWidth = 1 + Math.random() * 2
    g.beginPath()
    const y = Math.random() * 1024
    g.moveTo(0, y)
    g.bezierCurveTo(300, y + 20 * Math.random(), 700, y - 20 * Math.random(), 1024, y)
    g.stroke()
  }
  g.globalAlpha = 1
  // 网格
  const m = 62, span = 1024 - 2 * m, step = span / (N - 1)
  g.strokeStyle = '#4a3312'
  g.lineWidth = 2.4
  for (let i = 0; i < N; i++) {
    g.beginPath(); g.moveTo(m + i * step, m); g.lineTo(m + i * step, 1024 - m); g.stroke()
    g.beginPath(); g.moveTo(m, m + i * step); g.lineTo(1024 - m, m + i * step); g.stroke()
  }
  // 星位
  g.fillStyle = '#4a3312'
  for (const [x, y] of [[3, 3], [11, 3], [3, 11], [11, 11], [7, 7]]) {
    g.beginPath(); g.arc(m + x * step, m + y * step, 7, 0, Math.PI * 2); g.fill()
  }
  // 清漆光泽 + 四周暗角,更像上过蜡的实木
  const sheen = g.createRadialGradient(360, 300, 60, 512, 512, 900)
  sheen.addColorStop(0, 'rgba(255,255,255,0.10)')
  sheen.addColorStop(0.4, 'rgba(255,255,255,0)')
  sheen.addColorStop(1, 'rgba(30,18,4,0.22)')
  g.fillStyle = sheen
  g.fillRect(0, 0, 1024, 1024)
  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = 4
  return tex
}

export class GomokuScene {
  constructor(canvas, { onTapCell } = {}) {
    this.canvas = canvas
    this.onTapCell = onTapCell
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    this.scene = new THREE.Scene()
    this.camera = new THREE.PerspectiveCamera(46, 1, 0.1, 120)
    this.portrait = false

    const boardGeo = new THREE.BoxGeometry(HALF * 2 + 1.1, 0.5, HALF * 2 + 1.1)
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

    this.stoneGeo = new THREE.SphereGeometry(S * 0.44, 26, 18)
    // 清漆材质:云子般的温润光泽
    this.blackMat = new THREE.MeshPhysicalMaterial({
      color: 0x181b23, roughness: 0.32, metalness: 0.1, clearcoat: 1, clearcoatRoughness: 0.18,
    })
    this.whiteMat = new THREE.MeshPhysicalMaterial({
      color: 0xf4f0e4, roughness: 0.38, metalness: 0.02, clearcoat: 0.8, clearcoatRoughness: 0.25,
    })
    this.stoneGroup = new THREE.Group()
    this.fxGroup = new THREE.Group()
    this.scene.add(this.stoneGroup, this.fxGroup)
    this.stones = new Map()   // "x,y" → mesh
    this.marker = this._makeMarker()
    this.ghost = new THREE.Mesh(this.stoneGeo, new THREE.MeshStandardMaterial({
      color: 0xf5c145, transparent: true, opacity: 0.4, roughness: 0.4,
    }))
    this.ghost.visible = false
    this.ghost.scale.y = 0.55
    this.scene.add(this.marker, this.ghost)

    this.raycaster = new THREE.Raycaster()
    this.pointer = new THREE.Vector2()
    canvas.addEventListener('pointerdown', (e) => this._onTap(e))
    canvas.addEventListener('pointermove', (e) => this._onMove(e))
    canvas.addEventListener('pointerleave', () => { this.ghost.visible = false })

    this._raf = 0
    this._loop()
  }

  _makeMarker() {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(S * 0.5, S * 0.62, 32),
      new THREE.MeshBasicMaterial({ color: 0xf5c145, transparent: true, opacity: 0.95, side: THREE.DoubleSide }),
    )
    ring.rotation.x = -Math.PI / 2
    ring.visible = false
    // 呼吸脉冲,最后一手一眼可见
    gsap.to(ring.material, { opacity: 0.45, duration: 0.9, yoyo: true, repeat: -1, ease: 'sine.inOut' })
    return ring
  }

  setLowSpec(on) {
    this.renderer.setPixelRatio(on ? 1 : Math.min(devicePixelRatio, 2))
  }

  _layoutCamera() {
    if (this.portrait) {
      this.camera.fov = 58
      this.camera.position.set(0, 15.2, 8.2)
      this.camera.lookAt(0, 0, -0.4)
    } else {
      this.camera.fov = 45
      this.camera.position.set(0, 12.6, 9.4)
      this.camera.lookAt(0, 0, -0.4)
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

  _cellPos(x, y) {
    return new THREE.Vector3(x * S - HALF, 0.26, y * S - HALF)
  }

  /** 快照重绘:board[y][x] ∈ -1/0/1;stoneOfSeat0 'black'|'white' */
  setBoard(board, blackSeat, lastMove, winLine) {
    if (!board) { this.reset(); return }
    const want = new Set()
    for (let y = 0; y < N; y++) {
      for (let x = 0; x < N; x++) {
        const v = board[y][x]
        if (v === -1) continue
        const key = `${x},${y}`
        want.add(key)
        if (!this.stones.has(key)) {
          const isBlack = v === blackSeat
          const mesh = new THREE.Mesh(this.stoneGeo, isBlack ? this.blackMat : this.whiteMat)
          mesh.scale.y = 0.55
          mesh.position.copy(this._cellPos(x, y))
          this.stoneGroup.add(mesh)
          this.stones.set(key, mesh)
        }
      }
    }
    for (const [key, mesh] of this.stones) {
      if (!want.has(key)) {
        this.stoneGroup.remove(mesh)
        this.stones.delete(key)
      }
    }
    if (lastMove) {
      this.marker.visible = true
      this.marker.position.copy(this._cellPos(lastMove.x, lastMove.y)).setY(0.28)
    } else {
      this.marker.visible = false
    }
    if (winLine?.length) this._glowLine(winLine)
  }

  animatePlace(x, y) {
    const key = `${x},${y}`
    const mesh = this.stones.get(key)
    if (!mesh) return
    const target = mesh.position.y
    mesh.position.y = target + 2.2
    gsap.to(mesh.position, { y: target, duration: 0.24, ease: 'bounce.out' })
  }

  _glowLine(cells) {
    for (const [x, y] of cells) {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(S * 0.46, S * 0.6, 32),
        new THREE.MeshBasicMaterial({ color: 0x3ddc97, transparent: true, opacity: 0.9, side: THREE.DoubleSide }),
      )
      ring.rotation.x = -Math.PI / 2
      ring.position.copy(this._cellPos(x, y)).setY(0.29)
      this.fxGroup.add(ring)
      gsap.fromTo(ring.scale, { x: 0.2, y: 0.2, z: 0.2 }, { x: 1, y: 1, z: 1, duration: 0.45, ease: 'back.out(2)' })
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
    const x = Math.round((hit.point.x + HALF) / S)
    const y = Math.round((hit.point.z + HALF) / S)
    if (x < 0 || x >= N || y < 0 || y >= N) return null
    return { x, y }
  }

  _onTap(e) {
    const cell = this._cellFromEvent(e)
    if (cell) this.onTapCell?.(cell.x, cell.y)
  }

  _onMove(e) {
    if (e.pointerType !== 'mouse') return
    const cell = this._cellFromEvent(e)
    if (cell && !this.stones.has(`${cell.x},${cell.y}`) && this.hoverEnabled) {
      this.ghost.visible = true
      this.ghost.position.copy(this._cellPos(cell.x, cell.y))
    } else {
      this.ghost.visible = false
    }
  }

  setHoverEnabled(on) {
    this.hoverEnabled = on
    if (!on) this.ghost.visible = false
  }

  reset() {
    for (const [, mesh] of this.stones) this.stoneGroup.remove(mesh)
    this.stones.clear()
    this.marker.visible = false
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
    this.stoneGeo.dispose()
    this.renderer.dispose()
  }
}
