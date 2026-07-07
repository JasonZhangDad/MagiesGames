/* 3D 麻将桌:立牌手牌 + 四方牌河 + 出牌飞行 + 胡牌粒子。快照全量重绘,事件只做动画。 */
import * as THREE from 'three'
import gsap from 'gsap'
import { kindOf, tileBackTexture, tileFaceTexture } from './mahjongTiles'

const TW = 0.92
const TH = 1.28
const TD = 0.5

function feltTexture() {
  const S = 1024
  const c = document.createElement('canvas')
  c.width = c.height = S
  const g = c.getContext('2d')
  const grad = g.createRadialGradient(S / 2, S / 2, 80, S / 2, S / 2, S * 0.72)
  grad.addColorStop(0, '#1e6247')
  grad.addColorStop(0.6, '#134736')
  grad.addColorStop(1, '#092c22')
  g.fillStyle = grad
  g.fillRect(0, 0, S, S)
  // 绒布纤维噪点
  for (let i = 0; i < 2600; i++) {
    g.fillStyle = `rgba(255,255,255,${0.012 + Math.random() * 0.02})`
    g.fillRect(Math.random() * S, Math.random() * S, 1.5, 1.5)
  }
  // 金色双线牌区框 + 四角回纹点缀
  g.strokeStyle = 'rgba(245, 193, 69, 0.28)'
  g.lineWidth = 4
  g.strokeRect(180, 180, S - 360, S - 360)
  g.strokeStyle = 'rgba(245, 193, 69, 0.12)'
  g.lineWidth = 2
  g.strokeRect(196, 196, S - 392, S - 392)
  g.strokeStyle = 'rgba(245, 193, 69, 0.35)'
  g.lineWidth = 3
  for (const [x, y, dx, dy] of [[180, 180, 1, 1], [S - 180, 180, -1, 1], [180, S - 180, 1, -1], [S - 180, S - 180, -1, -1]]) {
    g.beginPath()
    g.moveTo(x + dx * 46, y)
    g.lineTo(x + dx * 46, y + dy * 16)
    g.lineTo(x + dx * 16, y + dy * 16)
    g.lineTo(x + dx * 16, y + dy * 46)
    g.lineTo(x, y + dy * 46)
    g.stroke()
  }
  // 中央徽记:同心环 + 菱形
  g.strokeStyle = 'rgba(245, 193, 69, 0.10)'
  g.lineWidth = 3
  g.beginPath(); g.arc(S / 2, S / 2, 130, 0, Math.PI * 2); g.stroke()
  g.beginPath(); g.arc(S / 2, S / 2, 112, 0, Math.PI * 2); g.stroke()
  g.save()
  g.translate(S / 2, S / 2)
  g.rotate(Math.PI / 4)
  g.strokeRect(-64, -64, 128, 128)
  g.restore()
  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = 4
  return tex
}

function roundedRectShape(w, h, r) {
  const s = new THREE.Shape()
  const x = -w / 2
  const y = -h / 2
  s.moveTo(x + r, y)
  s.lineTo(x + w - r, y)
  s.quadraticCurveTo(x + w, y, x + w, y + r)
  s.lineTo(x + w, y + h - r)
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
  s.lineTo(x + r, y + h)
  s.quadraticCurveTo(x, y + h, x, y + h - r)
  s.lineTo(x, y + r)
  s.quadraticCurveTo(x, y, x + r, y)
  return s
}

function normalizeUv(geometry) {
  geometry.computeBoundingBox()
  const bb = geometry.boundingBox
  const uv = geometry.attributes.uv
  const pos = geometry.attributes.position
  for (let i = 0; i < uv.count; i++) {
    uv.setXY(i,
      (pos.getX(i) - bb.min.x) / (bb.max.x - bb.min.x),
      (pos.getY(i) - bb.min.y) / (bb.max.y - bb.min.y))
  }
  uv.needsUpdate = true
  return geometry
}

export class MahjongScene {
  constructor(canvas, { onTapTile } = {}) {
    this.canvas = canvas
    this.onTapTile = onTapTile
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    this.scene = new THREE.Scene()
    this.camera = new THREE.PerspectiveCamera(46, 1, 0.1, 120)
    this.portrait = false

    this._buildTable()
    this.tileGeo = new THREE.BoxGeometry(TW, TH, TD)
    this.bodyMat = new THREE.MeshStandardMaterial({ color: 0xf3ecd8, roughness: 0.4 })
    this.backMat = new THREE.MeshStandardMaterial({ map: tileBackTexture(), roughness: 0.5 })

    this.handGroup = new THREE.Group()
    this.riverGroup = new THREE.Group()
    this.oppoGroup = new THREE.Group()
    this.fxGroup = new THREE.Group()
    this.scene.add(this.handGroup, this.riverGroup, this.oppoGroup, this.fxGroup)
    this._oppoCounts = null

    this.handMeshes = new Map()
    this.hand = []
    this.drawnTile = null
    this.selected = new Set()
    this.raycaster = new THREE.Raycaster()
    this.pointer = new THREE.Vector2()
    canvas.addEventListener('pointerdown', (e) => this._onTap(e))

    this._raf = 0
    this._loop()
  }

  _buildTable() {
    // 胡桃木包边:立体挤出,比平面金圈更有实木牌桌质感
    const rim = new THREE.Mesh(
      new THREE.ExtrudeGeometry(roundedRectShape(17.4, 14.2, 3.0), {
        depth: 0.55, bevelEnabled: true, bevelThickness: 0.12, bevelSize: 0.12, bevelSegments: 2, curveSegments: 24,
      }),
      new THREE.MeshStandardMaterial({ color: 0x5d3f22, roughness: 0.55, metalness: 0.08 }),
    )
    rim.rotation.x = -Math.PI / 2
    rim.position.y = -0.62
    // 包边上的金色装饰线
    const trim = new THREE.Mesh(
      new THREE.ShapeGeometry(roundedRectShape(16.7, 13.5, 2.7), 24),
      new THREE.MeshStandardMaterial({ color: 0xc89b3c, roughness: 0.35, metalness: 0.7 }),
    )
    trim.rotation.x = -Math.PI / 2
    trim.position.y = -0.015
    const felt = new THREE.Mesh(
      normalizeUv(new THREE.ShapeGeometry(roundedRectShape(16.2, 13, 2.4), 24)),
      new THREE.MeshStandardMaterial({ map: feltTexture(), roughness: 0.95 }),
    )
    felt.rotation.x = -Math.PI / 2
    this.scene.add(rim, trim, felt)
    this.scene.add(new THREE.HemisphereLight(0xd8ecff, 0x1a2e28, 1.1))
    const key = new THREE.DirectionalLight(0xfff2d8, 1.7)
    key.position.set(3, 15, 5)
    // 桌面中央暖光,牌面更润
    const warm = new THREE.PointLight(0xffd9a0, 9, 22)
    warm.position.set(0, 7, 1.5)
    const cyan = new THREE.PointLight(0x35e0ff, 15, 28)
    cyan.position.set(-8, 5, -3)
    const violet = new THREE.PointLight(0x8b7bff, 12, 28)
    violet.position.set(8, 5, -3)
    this.scene.add(key, warm, cyan, violet)
  }

  setLowSpec(on) {
    this.renderer.setPixelRatio(on ? 1 : Math.min(devicePixelRatio, 2))
  }

  _layoutCamera() {
    if (this.portrait) {
      this.camera.fov = 60
      this.camera.position.set(0, 18.5, 12.4)
      this.camera.lookAt(0, 0, -1.2)
    } else {
      this.camera.fov = 47
      this.camera.position.set(0, 14.4, 12.2)
      this.camera.lookAt(0, 0.2, -0.8)
    }
    this.camera.updateProjectionMatrix()
  }

  resize() {
    const w = this.canvas.clientWidth
    const h = this.canvas.clientHeight
    if (!w || !h) return
    const portrait = h > w
    if (this.canvas.width !== Math.floor(w * this.renderer.getPixelRatio())
      || this.canvas.height !== Math.floor(h * this.renderer.getPixelRatio())
      || portrait !== this.portrait) {
      this.portrait = portrait
      this.renderer.setSize(w, h, false)
      this.camera.aspect = w / h
      this._layoutCamera()
      this._placeHand(false)
      this._renderRivers()
    }
  }

  _tileMesh(tile, faceUp = true) {
    const mats = [this.bodyMat, this.bodyMat, this.bodyMat, this.bodyMat,
      faceUp ? new THREE.MeshBasicMaterial({ map: tileFaceTexture(kindOf(tile)) }) : this.backMat,
      this.backMat]
    const m = new THREE.Mesh(this.tileGeo, mats)
    m.userData.tile = tile
    return m
  }

  // ---------- 我的手牌 ----------

  setMyHand(tiles, drawn, selected) {
    this.hand = [...tiles]
    this.drawnTile = drawn
    // selected 可以是单张或数组(换三张多选)
    this.selected = new Set(Array.isArray(selected) ? selected
      : selected === null || selected === undefined ? [] : [selected])
    const keep = new Set(tiles)
    for (const [id, mesh] of this.handMeshes) {
      if (!keep.has(id)) {
        this.handGroup.remove(mesh)
        mesh.material[4]?.dispose?.()
        this.handMeshes.delete(id)
      }
    }
    for (const t of tiles) {
      if (!this.handMeshes.has(t)) {
        const mesh = this._tileMesh(t)
        mesh.material = mesh.material.map(mm => mm)
        this.handGroup.add(mesh)
        this.handMeshes.set(t, mesh)
      }
    }
    this._placeHand(true)
  }

  _placeHand(animate) {
    const n = this.hand.length
    if (!n) return
    const scale = this.portrait ? 0.78 : 1
    const anchorY = this.portrait ? 2.4 : 1.5
    const anchorZ = this.portrait ? 6.4 : 6.9
    // 摸的那张牌排最后并留缝
    const ordered = this.hand.filter(t => t !== this.drawnTile).sort((a, b) => a - b)
    if (this.drawnTile !== null && this.hand.includes(this.drawnTile)) ordered.push(this.drawnTile)
    const step = Math.min(TW * scale + 0.06, (this.portrait ? 8.6 : 12.5) / n)
    ordered.forEach((t, i) => {
      const mesh = this.handMeshes.get(t)
      if (!mesh) return
      const gapExtra = (this.drawnTile !== null && i === n - 1) ? step * 0.45 : 0
      const x = (i - (n - 1) / 2) * step + gapExtra
      const y = anchorY + (this.selected.has(t) ? 0.42 : 0)
      mesh.quaternion.copy(this.camera.quaternion)
      mesh.renderOrder = 100 + i
      mesh.scale.setScalar(scale)
      gsap.killTweensOf(mesh.position)
      if (animate) {
        gsap.to(mesh.position, { x, y, z: anchorZ + i * 0.01, duration: 0.22, ease: 'power2.out' })
      } else {
        mesh.position.set(x, y, anchorZ + i * 0.01)
      }
    })
  }

  // ---------- 对手立牌:只见牌背,人数感扑面而来 ----------

  /** counts = [右, 对家, 左] 各家剩余手牌数(胡牌/离场传 0) */
  setOpponentHands(counts) {
    const key = counts.join(',')
    if (this._oppoCounts === key) return
    this._oppoCounts = key
    while (this.oppoGroup.children.length) this.oppoGroup.remove(this.oppoGroup.children[0])
    const s = 0.82
    const step = TW * s + 0.045
    const conf = [
      { pos: (i, n) => [6.5, 0.55, ((n - 1) / 2 - i) * step], rotY: -Math.PI / 2 },  // 右
      { pos: (i, n) => [(i - (n - 1) / 2) * step, 0.55, -5.35], rotY: Math.PI },     // 对家
      { pos: (i, n) => [-6.5, 0.55, (i - (n - 1) / 2) * step], rotY: Math.PI / 2 },  // 左
    ]
    counts.forEach((n, idx) => {
      const cfg = conf[idx]
      for (let i = 0; i < n; i++) {
        const m = new THREE.Mesh(this.tileGeo,
          [this.bodyMat, this.bodyMat, this.bodyMat, this.bodyMat, this.backMat, this.backMat])
        const [x, y, z] = cfg.pos(i, n)
        m.position.set(x, y, z)
        m.rotation.y = cfg.rotY
        m.scale.setScalar(s)
        this.oppoGroup.add(m)
      }
    })
  }

  // ---------- 牌河 ----------

  setRivers(discardsByRel) {
    this._riverData = discardsByRel
    this._renderRivers()
  }

  _renderRivers() {
    while (this.riverGroup.children.length) {
      const m = this.riverGroup.children[0]
      this.riverGroup.remove(m)
      if (Array.isArray(m.material)) m.material[4]?.dispose?.()
    }
    if (!this._riverData) return
    const s = this.portrait ? 0.6 : 0.68
    const conf = [
      { origin: [0, 0.28, 2.0], dx: [1, 0], dy: [0, 1], rotZ: 0 },        // 我:向下堆
      { origin: [3.6, 0.28, 0], dx: [0, 1], dy: [1, 0], rotZ: Math.PI / 2 },   // 右
      { origin: [0, 0.28, -2.4], dx: [-1, 0], dy: [0, -1], rotZ: Math.PI },    // 对家
      { origin: [-3.6, 0.28, 0], dx: [0, -1], dy: [-1, 0], rotZ: -Math.PI / 2 }, // 左
    ]
    this._riverData.forEach((tiles, rel) => {
      const cfg = conf[rel]
      tiles.forEach((t, i) => {
        const row = Math.floor(i / 6)
        const col = i % 6
        const mesh = this._tileMesh(t)
        mesh.rotation.x = -Math.PI / 2
        mesh.rotation.z = cfg.rotZ
        mesh.scale.setScalar(s)
        const ox = (col - 2.5) * (TW * s + 0.06)
        const oy = row * (TH * s + 0.06)
        mesh.position.set(
          cfg.origin[0] + cfg.dx[0] * ox + cfg.dy[0] * oy,
          cfg.origin[1],
          cfg.origin[2] + cfg.dx[1] * ox + cfg.dy[1] * oy,
        )
        this.riverGroup.add(mesh)
      })
    })
  }

  animateDiscard(rel, tile) {
    const from = [
      new THREE.Vector3(0, 2, 5.5), new THREE.Vector3(7, 2.4, -1),
      new THREE.Vector3(0, 2.6, -5.5), new THREE.Vector3(-7, 2.4, -1),
    ][rel]
    const to = new THREE.Vector3(
      rel === 1 ? 3.2 : rel === 3 ? -3.2 : 0,
      0.5,
      rel === 0 ? 1.8 : rel === 2 ? -2.2 : 0,
    )
    const mesh = this._tileMesh(tile)
    mesh.position.copy(from)
    mesh.rotation.x = -Math.PI / 2
    this.fxGroup.add(mesh)
    // 抛物线飞行 + 翻转落桌
    gsap.to(mesh.position, { x: to.x, z: to.z, duration: 0.34, ease: 'power1.in' })
    gsap.to(mesh.position, {
      y: 2.6, duration: 0.15, ease: 'power2.out', yoyo: true, repeat: 1,
      onComplete: () => {
        mesh.position.y = to.y
        this._landRipple(to)
        gsap.delayedCall(0.12, () => this.fxGroup.remove(mesh))
      },
    })
    gsap.to(mesh.rotation, { z: mesh.rotation.z + Math.PI * 2, duration: 0.34, ease: 'power1.inOut' })
  }

  /** 落桌金色涟漪 */
  _landRipple(pos) {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.25, 0.4, 32),
      new THREE.MeshBasicMaterial({
        color: 0xf5c145, transparent: true, opacity: 0.75,
        side: THREE.DoubleSide, depthWrite: false,
      }),
    )
    ring.rotation.x = -Math.PI / 2
    ring.position.set(pos.x, 0.05, pos.z)
    this.fxGroup.add(ring)
    gsap.to(ring.scale, { x: 3.2, y: 3.2, z: 3.2, duration: 0.5, ease: 'power2.out' })
    gsap.to(ring.material, {
      opacity: 0, duration: 0.5, ease: 'power1.out',
      onComplete: () => { this.fxGroup.remove(ring); ring.geometry.dispose(); ring.material.dispose() },
    })
  }

  celebrate(win) {
    if (win) {
      // 金环冲击波 ×2
      for (const delay of [0, 0.22]) {
        const ring = new THREE.Mesh(
          new THREE.RingGeometry(0.5, 0.85, 48),
          new THREE.MeshBasicMaterial({
            color: delay ? 0x35e0ff : 0xf5c145, transparent: true, opacity: 0.85,
            side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending,
          }),
        )
        ring.rotation.x = -Math.PI / 2
        ring.position.y = 0.4
        this.fxGroup.add(ring)
        gsap.to(ring.scale, { x: 11, y: 11, z: 11, duration: 1.1, delay, ease: 'power2.out' })
        gsap.to(ring.material, {
          opacity: 0, duration: 1.1, delay, ease: 'power1.out',
          onComplete: () => { this.fxGroup.remove(ring); ring.geometry.dispose(); ring.material.dispose() },
        })
      }
    }
    const N = win ? 220 : 50
    const geo = new THREE.BufferGeometry()
    const pos = new Float32Array(N * 3)
    const vel = []
    for (let i = 0; i < N; i++) {
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
        for (let i = 0; i < N; i++) {
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

  _onTap(e) {
    const rect = this.canvas.getBoundingClientRect()
    this.pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
    this.pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
    this.raycaster.setFromCamera(this.pointer, this.camera)
    const hits = this.raycaster.intersectObjects([...this.handMeshes.values()])
    if (hits.length) {
      const top = hits.reduce((a, b) => (a.object.renderOrder >= b.object.renderOrder ? a : b))
      this.onTapTile?.(top.object.userData.tile)
    }
  }

  _loop() {
    this._raf = requestAnimationFrame(() => this._loop())
    this.resize()
    this.renderer.render(this.scene, this.camera)
  }

  reset() {
    this.setMyHand([], null, null)
    this.setRivers([[], [], [], []])
    this._oppoCounts = null
    while (this.oppoGroup.children.length) this.oppoGroup.remove(this.oppoGroup.children[0])
  }

  dispose() {
    cancelAnimationFrame(this._raf)
    this.reset()
    this.tileGeo.dispose()
    this.renderer.dispose()
  }
}
