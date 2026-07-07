/* 3D 对局桌:牌桌、扇形手牌、发牌/出牌动画、底牌翻转、胜利粒子。
   手牌用公告板(始终面向相机)保证任何屏幕比例下都清晰可读。 */
import * as THREE from 'three'
import gsap from 'gsap'
import { CARD_RATIO, backTexture, faceTexture } from './cardTexture'

const CARD_W = 1.5
const DECK_POS = new THREE.Vector3(0, 2.2, -3.4)

function feltTexture() {
  const S = 1024
  const c = document.createElement('canvas')
  c.width = c.height = S
  const g = c.getContext('2d')
  const grad = g.createRadialGradient(S / 2, S / 2, 80, S / 2, S / 2, S * 0.7)
  grad.addColorStop(0, '#175061')
  grad.addColorStop(0.65, '#0d3038')
  grad.addColorStop(1, '#071a21')
  g.fillStyle = grad
  g.fillRect(0, 0, S, S)
  // 绒布纤维噪点
  for (let i = 0; i < 2400; i++) {
    g.fillStyle = `rgba(255,255,255,${0.012 + Math.random() * 0.018})`
    g.fillRect(Math.random() * S, Math.random() * S, 1.5, 1.5)
  }
  // 金色同心装饰环 + 中央菱形徽记
  g.strokeStyle = 'rgba(245, 193, 69, 0.14)'
  g.lineWidth = 4
  g.beginPath(); g.arc(S / 2, S / 2, 360, 0, Math.PI * 2); g.stroke()
  g.strokeStyle = 'rgba(245, 193, 69, 0.07)'
  g.lineWidth = 2
  g.beginPath(); g.arc(S / 2, S / 2, 330, 0, Math.PI * 2); g.stroke()
  g.save()
  g.translate(S / 2, S / 2)
  g.rotate(Math.PI / 4)
  g.strokeStyle = 'rgba(245, 193, 69, 0.09)'
  g.lineWidth = 3
  g.strokeRect(-70, -70, 140, 140)
  g.restore()
  const tex = new THREE.CanvasTexture(c)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.anisotropy = 4
  return tex
}

function glowTexture(inner = 'rgba(245,193,69,0.55)') {
  const c = document.createElement('canvas')
  c.width = c.height = 128
  const g = c.getContext('2d')
  const grad = g.createRadialGradient(64, 64, 2, 64, 64, 64)
  grad.addColorStop(0, inner)
  grad.addColorStop(1, 'rgba(245,193,69,0)')
  g.fillStyle = grad
  g.fillRect(0, 0, 128, 128)
  return new THREE.CanvasTexture(c)
}

function normalizeUv(geometry) {
  // ShapeGeometry 的 UV 是形状坐标,重映射到 0-1 让贴图铺满
  geometry.computeBoundingBox()
  const bb = geometry.boundingBox
  const uv = geometry.attributes.uv
  const posAttr = geometry.attributes.position
  for (let i = 0; i < uv.count; i++) {
    uv.setXY(i,
      (posAttr.getX(i) - bb.min.x) / (bb.max.x - bb.min.x),
      (posAttr.getY(i) - bb.min.y) / (bb.max.y - bb.min.y))
  }
  uv.needsUpdate = true
  return geometry
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

export class TableScene {
  constructor(canvas, { onToggleCard } = {}) {
    this.canvas = canvas
    this.onToggleCard = onToggleCard
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
    this.scene = new THREE.Scene()
    this.camera = new THREE.PerspectiveCamera(46, 1, 0.1, 120)
    this.portrait = false

    this._buildTable()
    this._buildLights()
    this._buildStars()

    this.cardGeo = new THREE.PlaneGeometry(CARD_W, CARD_W * CARD_RATIO)
    this.handGroup = new THREE.Group()
    this.trickGroups = [new THREE.Group(), new THREE.Group(), new THREE.Group()]
    this.bottomGroup = new THREE.Group()
    this.scene.add(this.handGroup, this.bottomGroup, ...this.trickGroups)

    this.handMeshes = new Map() // cardId -> mesh
    this.selected = new Set()
    this.hand = []
    this.raycaster = new THREE.Raycaster()
    this.pointer = new THREE.Vector2()
    this._dragToggled = null

    canvas.addEventListener('pointerdown', (e) => this._onPointer(e, true))
    canvas.addEventListener('pointermove', (e) => this._onPointer(e, false))
    addEventListener('pointerup', () => { this._dragToggled = null })

    this._raf = 0
    this._clock = new THREE.Clock()
    this._loop()
  }

  // ---------- 场景搭建 ----------

  _buildTable() {
    // 胡桃木立体包边 + 金色饰线,取代原来的平面金圈
    const rim = new THREE.Mesh(
      new THREE.ExtrudeGeometry(roundedRectShape(18.2, 13.4, 3.7), {
        depth: 0.55, bevelEnabled: true, bevelThickness: 0.12, bevelSize: 0.12, bevelSegments: 2, curveSegments: 24,
      }),
      new THREE.MeshStandardMaterial({ color: 0x54391f, roughness: 0.55, metalness: 0.08 }),
    )
    rim.rotation.x = -Math.PI / 2
    rim.position.y = -0.62
    const trim = new THREE.Mesh(
      new THREE.ShapeGeometry(roundedRectShape(17.5, 12.6, 3.45), 24),
      new THREE.MeshStandardMaterial({ color: 0xc89b3c, roughness: 0.35, metalness: 0.7 }),
    )
    trim.rotation.x = -Math.PI / 2
    trim.position.y = -0.015
    const felt = new THREE.Mesh(
      normalizeUv(new THREE.ShapeGeometry(roundedRectShape(17, 12, 3.2), 24)),
      new THREE.MeshStandardMaterial({ map: feltTexture(), roughness: 0.92, metalness: 0.05 }),
    )
    felt.rotation.x = -Math.PI / 2
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTexture('rgba(53,224,255,0.20)'),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }))
    glow.scale.set(20, 12, 1)
    glow.position.y = 0.4
    this.scene.add(rim, trim, felt, glow)
  }

  _buildLights() {
    this.scene.add(new THREE.HemisphereLight(0xcfe6ff, 0x1a2340, 1.1))
    const key = new THREE.DirectionalLight(0xfff2d8, 1.6)
    key.position.set(4, 14, 6)
    // 中央暖光让牌面更润
    const warm = new THREE.PointLight(0xffd9a0, 10, 24)
    warm.position.set(0, 7, 2)
    const cyan = new THREE.PointLight(0x35e0ff, 22, 30)
    cyan.position.set(-9, 5, -4)
    const violet = new THREE.PointLight(0x8b7bff, 18, 30)
    violet.position.set(9, 5, -4)
    this.scene.add(key, warm, cyan, violet)
  }

  _buildStars() {
    const N = 260
    const geo = new THREE.BufferGeometry()
    const pos = new Float32Array(N * 3)
    for (let i = 0; i < N; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 70
      pos[i * 3 + 1] = 4 + Math.random() * 26
      pos[i * 3 + 2] = -14 - Math.random() * 40
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    this.stars = new THREE.Points(geo, new THREE.PointsMaterial({
      color: 0x9fc7ff, size: 0.07, transparent: true, opacity: 0.6, depthWrite: false,
    }))
    this.scene.add(this.stars)
  }

  setLowSpec(on) {
    this.renderer.setPixelRatio(on ? 1 : Math.min(devicePixelRatio, 2))
    if (this.stars) this.stars.visible = !on
  }

  // ---------- 布局 ----------

  _layoutCamera() {
    if (this.portrait) {
      this.camera.fov = 58
      this.camera.position.set(0, 17.5, 13.2)
      this.camera.lookAt(0, 0.4, -1.6)
    } else {
      this.camera.fov = 46
      this.camera.position.set(0, 13.2, 12.8)
      this.camera.lookAt(0, 0.6, -0.9)
    }
    this.camera.updateProjectionMatrix()
  }

  _handAnchor() {
    return this.portrait ? new THREE.Vector3(0, 2.6, 6.6) : new THREE.Vector3(0, 1.9, 7.0)
  }

  _handLayout(n) {
    const scale = this.portrait ? 0.86 : 1
    const maxW = this.portrait ? 6.6 : 10.5
    const step = n > 1 ? Math.min(CARD_W * scale * 0.46, maxW / (n - 1)) : 0
    return { scale, step }
  }

  _seatOrigin(rel) {
    // rel: 0 我(下) 1 右(下家) 2 左(上家)
    if (rel === 1) return new THREE.Vector3(this.portrait ? 4.6 : 7.6, 2.4, -2.2)
    if (rel === 2) return new THREE.Vector3(this.portrait ? -4.6 : -7.6, 2.4, -2.2)
    return this._handAnchor().clone()
  }

  _trickSlot(rel) {
    if (this.portrait) {
      if (rel === 1) return { pos: new THREE.Vector3(1.9, 0.4, -0.4), scale: 0.72 }
      if (rel === 2) return { pos: new THREE.Vector3(-1.9, 0.4, -0.4), scale: 0.72 }
      return { pos: new THREE.Vector3(0, 0.4, 2.6), scale: 0.8 }
    }
    if (rel === 1) return { pos: new THREE.Vector3(4.1, 0.4, -1.2), scale: 0.82 }
    if (rel === 2) return { pos: new THREE.Vector3(-4.1, 0.4, -1.2), scale: 0.82 }
    return { pos: new THREE.Vector3(0, 0.4, 2.9), scale: 0.9 }
  }

  resize() {
    const w = this.canvas.clientWidth
    const h = this.canvas.clientHeight
    if (!w || !h) return
    const need = this.canvas.width !== Math.floor(w * this.renderer.getPixelRatio())
    const portrait = h > w
    if (need || portrait !== this.portrait) {
      this.portrait = portrait
      this.renderer.setSize(w, h, false)
      this.camera.aspect = w / h
      this._layoutCamera()
      this._placeHand(false)
      this._placeBottom()
      for (let rel = 0; rel < 3; rel++) this._placeTrick(rel)
    }
  }

  // ---------- 手牌 ----------

  setMyHand(cards, { deal = false } = {}) {
    const same = cards.length === this.hand.length && cards.every((c, i) => c === this.hand[i])
    this.hand = [...cards]
    const keep = new Set(cards)
    for (const [id, mesh] of this.handMeshes) {
      if (!keep.has(id)) {
        this.handGroup.remove(mesh)
        mesh.material.dispose()
        this.handMeshes.delete(id)
        this.selected.delete(id)
      }
    }
    for (const id of cards) {
      if (!this.handMeshes.has(id)) {
        // 深度测试关闭:扇形弧线会让相邻牌深度关系反转,改用 renderOrder 严格排序
        const mesh = new THREE.Mesh(this.cardGeo, new THREE.MeshBasicMaterial({
          map: faceTexture(id), transparent: true, depthTest: false, depthWrite: false,
        }))
        mesh.userData.cardId = id
        this.handGroup.add(mesh)
        this.handMeshes.set(id, mesh)
      }
    }
    if (deal) this._dealAnimation()
    else if (!same) this._placeHand(true)
  }

  setSelected(ids) {
    this.selected = new Set(ids)
    this._placeHand(true)
  }

  _cardTargets() {
    const n = this.hand.length
    const anchor = this._handAnchor()
    const { scale, step } = this._handLayout(n)
    const targets = []
    for (let i = 0; i < n; i++) {
      const x = (i - (n - 1) / 2) * step
      const arc = -Math.pow(Math.abs(i - (n - 1) / 2) / Math.max(1, (n - 1) / 2), 2) * 0.35
      targets.push({
        x: anchor.x + x,
        y: anchor.y + arc + (this.selected.has(this.hand[i]) ? 0.55 : 0),
        z: anchor.z + i * 0.012,
        rz: -(i - (n - 1) / 2) * 0.016,
        scale,
      })
    }
    return targets
  }

  _placeHand(animate) {
    const targets = this._cardTargets()
    this.hand.forEach((id, i) => {
      const mesh = this.handMeshes.get(id)
      if (!mesh) return
      const t = targets[i]
      mesh.quaternion.copy(this.camera.quaternion)
      mesh.rotateZ(t.rz)
      gsap.killTweensOf(mesh.position)
      gsap.killTweensOf(mesh.scale)
      if (animate) {
        gsap.to(mesh.position, { x: t.x, y: t.y, z: t.z, duration: 0.28, ease: 'power2.out' })
      } else {
        mesh.position.set(t.x, t.y, t.z)
      }
      mesh.scale.setScalar(t.scale)
      mesh.renderOrder = 100 + i
    })
  }

  _dealAnimation() {
    const targets = this._cardTargets()
    this.hand.forEach((id, i) => {
      const mesh = this.handMeshes.get(id)
      const t = targets[i]
      mesh.quaternion.copy(this.camera.quaternion)
      mesh.rotateZ(t.rz)
      mesh.position.copy(DECK_POS)
      mesh.scale.setScalar(0.3)
      mesh.renderOrder = 100 + i
      gsap.killTweensOf(mesh.position)
      gsap.to(mesh.position, {
        x: t.x, y: t.y, z: t.z, duration: 0.4, delay: i * 0.045, ease: 'power2.out',
      })
      gsap.to(mesh.scale, {
        x: t.scale, y: t.scale, z: t.scale, duration: 0.4, delay: i * 0.045,
      })
    })
  }

  // ---------- 出牌区 ----------

  setTrick(rel, cards, { animate = true } = {}) {
    const group = this.trickGroups[rel]
    this._clearGroup(group)
    group.userData.cards = cards
    const slot = this._trickSlot(rel)
    const step = Math.min(0.62 * slot.scale, (this.portrait ? 3.4 : 5.5) / Math.max(1, cards.length - 1) || 0.62)
    cards.forEach((id, i) => {
      const mesh = new THREE.Mesh(this.cardGeo, new THREE.MeshBasicMaterial({
        map: faceTexture(id), transparent: true,
      }))
      mesh.scale.setScalar(slot.scale)
      const tx = slot.pos.x + (i - (cards.length - 1) / 2) * step
      mesh.rotation.x = -Math.PI / 2 + 0.62
      mesh.renderOrder = 40 + i
      if (animate) {
        const from = this._seatOrigin(rel)
        mesh.position.copy(from)
        gsap.to(mesh.position, {
          x: tx, y: slot.pos.y + i * 0.012, z: slot.pos.z,
          duration: 0.32, delay: i * 0.03, ease: 'power2.out',
        })
      } else {
        mesh.position.set(tx, slot.pos.y + i * 0.012, slot.pos.z)
      }
      group.add(mesh)
    })
  }

  _placeTrick(rel) {
    const cards = this.trickGroups[rel].userData.cards
    if (cards?.length) this.setTrick(rel, cards, { animate: false })
  }

  clearTricks() {
    this.trickGroups.forEach((g) => {
      this._clearGroup(g)
      g.userData.cards = null
    })
  }

  // ---------- 底牌 ----------

  setBottom(cards, revealed) {
    this._clearGroup(this.bottomGroup)
    this.bottomGroup.userData.state = { cards, revealed }
    const y = this.portrait ? 5.2 : 4.6
    const list = cards?.length ? cards : [null, null, null]
    list.forEach((id, i) => {
      const mesh = new THREE.Mesh(this.cardGeo, new THREE.MeshBasicMaterial({
        map: revealed && id !== null ? faceTexture(id) : backTexture(),
        transparent: true,
      }))
      mesh.scale.setScalar(0.6)
      mesh.position.set((i - 1) * 1.06, y, -4.6)
      mesh.quaternion.copy(this.camera.quaternion)
      mesh.renderOrder = 5
      this.bottomGroup.add(mesh)
    })
  }

  revealBottom(cards) {
    // 翻牌动画:先转到侧立换贴图,再转回正面(平面翻满 180° 会背面剔除)
    this.bottomGroup.userData.state = { cards, revealed: true }
    this.bottomGroup.children.forEach((mesh, i) => {
      const baseY = mesh.rotation.y
      gsap.to(mesh.rotation, {
        y: baseY + Math.PI / 2, duration: 0.24, delay: i * 0.12, ease: 'power1.in',
        onComplete: () => {
          mesh.material.map = faceTexture(cards[i])
          mesh.material.needsUpdate = true
          gsap.to(mesh.rotation, { y: baseY, duration: 0.24, ease: 'power1.out' })
        },
      })
    })
  }

  _placeBottom() {
    const st = this.bottomGroup.userData.state
    if (st) this.setBottom(st.cards, st.revealed)
  }

  // ---------- 特效 ----------

  celebrate(win) {
    const N = win ? 240 : 60
    const geo = new THREE.BufferGeometry()
    const pos = new Float32Array(N * 3)
    const vel = []
    for (let i = 0; i < N; i++) {
      pos[i * 3] = 0
      pos[i * 3 + 1] = 2
      pos[i * 3 + 2] = 0
      vel.push(new THREE.Vector3(
        (Math.random() - 0.5) * 10,
        4 + Math.random() * 9,
        (Math.random() - 0.5) * 8,
      ))
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({
      color: win ? 0xf5c145 : 0x6b7ba8, size: win ? 0.16 : 0.1,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }))
    this.scene.add(pts)
    const state = { t: 0 }
    gsap.to(state, {
      t: 1, duration: 1.8, ease: 'power1.out',
      onUpdate: () => {
        const arr = geo.attributes.position.array
        for (let i = 0; i < N; i++) {
          arr[i * 3] = vel[i].x * state.t
          arr[i * 3 + 1] = 2 + vel[i].y * state.t - 7 * state.t * state.t
          arr[i * 3 + 2] = vel[i].z * state.t
        }
        geo.attributes.position.needsUpdate = true
        pts.material.opacity = 1 - state.t
      },
      onComplete: () => {
        this.scene.remove(pts)
        geo.dispose()
        pts.material.dispose()
      },
    })
  }

  bombFlash() {
    const flash = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glowTexture('rgba(255,120,80,0.9)'),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    }))
    flash.scale.set(1, 1, 1)
    flash.position.set(0, 2, 0)
    this.scene.add(flash)
    gsap.to(flash.scale, { x: 26, y: 16, duration: 0.5, ease: 'power2.out' })
    gsap.to(flash.material, {
      opacity: 0, duration: 0.55, ease: 'power1.in',
      onComplete: () => this.scene.remove(flash),
    })
    // 相机震动
    const cam = this.camera.position
    gsap.fromTo(cam, { y: cam.y + 0.28 }, { y: cam.y, duration: 0.4, ease: 'elastic.out(1.5, 0.3)' })
  }

  // ---------- 交互 ----------

  _onPointer(e, isDown) {
    if (!isDown && !(e.buttons & 1)) return
    if (isDown) this._dragToggled = new Set()
    if (!this._dragToggled) return
    const rect = this.canvas.getBoundingClientRect()
    this.pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
    this.pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
    this.raycaster.setFromCamera(this.pointer, this.camera)
    const hits = this.raycaster.intersectObjects([...this.handMeshes.values()])
    if (hits.length) {
      // 命中重叠的多张时取视觉上最靠前那张(renderOrder 最大)
      const top = hits.reduce((a, b) =>
        (a.object.renderOrder >= b.object.renderOrder ? a : b))
      const id = top.object.userData.cardId
      if (!this._dragToggled.has(id)) {
        this._dragToggled.add(id)
        this.onToggleCard?.(id)
      }
    }
  }

  // ---------- 主循环 ----------

  _loop() {
    this._raf = requestAnimationFrame(() => this._loop())
    this.resize()
    const t = this._clock.getElapsedTime()
    if (this.stars?.visible) this.stars.rotation.y = t * 0.004
    this.renderer.render(this.scene, this.camera)
  }

  _clearGroup(g) {
    while (g.children.length) {
      const m = g.children[0]
      g.remove(m)
      m.material?.dispose()
    }
  }

  reset() {
    this.clearTricks()
    this.setMyHand([])
    this._clearGroup(this.bottomGroup)
    this.bottomGroup.userData.state = null
  }

  dispose() {
    cancelAnimationFrame(this._raf)
    this.reset()
    this.cardGeo.dispose()
    this.renderer.dispose()
  }
}
