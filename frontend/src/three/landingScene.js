/* 落地页 3D 背景:星尘 + 漂浮旋转的扑克牌。 */
import * as THREE from 'three'
import { CARD_RATIO, backTexture, faceTexture } from './cardTexture'

export function createLandingScene(canvas) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2))
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100)
  camera.position.set(0, 0, 11)

  // 星尘
  const starGeo = new THREE.BufferGeometry()
  const N = 420
  const pos = new Float32Array(N * 3)
  for (let i = 0; i < N; i++) {
    pos[i * 3] = (Math.random() - 0.5) * 44
    pos[i * 3 + 1] = (Math.random() - 0.5) * 26
    pos[i * 3 + 2] = -6 - Math.random() * 26
  }
  starGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({
    color: 0x9fc7ff, size: 0.05, transparent: true, opacity: 0.75, depthWrite: false,
  }))
  scene.add(stars)

  // 漂浮卡牌(经典大牌面)
  const showcase = [53, 52, 48, 49, 44, 45, 40] // 大小王/2/2/A/A/K
  const cards = []
  const geo = new THREE.PlaneGeometry(1.7, 1.7 * CARD_RATIO)
  showcase.forEach((id, i) => {
    const useFace = i < 5
    const mat = new THREE.MeshBasicMaterial({
      map: useFace ? faceTexture(id) : backTexture(),
      transparent: true,
      side: THREE.DoubleSide,
    })
    const m = new THREE.Mesh(geo, mat)
    const angle = (i / showcase.length) * Math.PI * 2
    m.position.set(Math.cos(angle) * 5.9, Math.sin(angle) * 3.1, -2.5 - (i % 3))
    m.rotation.set(Math.random() * 0.5 - 0.25, Math.random() * 0.9 - 0.45, Math.random() * 0.6 - 0.3)
    m.userData = { angle, speed: 0.11 + i * 0.013, wob: Math.random() * Math.PI * 2 }
    scene.add(m)
    cards.push(m)
  })

  let px = 0
  let py = 0
  const onPointer = (e) => {
    const t = e.touches ? e.touches[0] : e
    px = (t.clientX / innerWidth - 0.5) * 2
    py = (t.clientY / innerHeight - 0.5) * 2
  }
  addEventListener('pointermove', onPointer, { passive: true })

  let raf = 0
  const clock = new THREE.Clock()
  function resize() {
    const w = canvas.clientWidth
    const h = canvas.clientHeight
    if (canvas.width !== w * renderer.getPixelRatio() || canvas.height !== h * renderer.getPixelRatio()) {
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
  }
  function loop() {
    raf = requestAnimationFrame(loop)
    resize()
    const t = clock.getElapsedTime()
    stars.rotation.z = t * 0.008
    cards.forEach((m) => {
      const a = m.userData.angle + t * m.userData.speed
      m.position.x = Math.cos(a) * 5.9
      m.position.y = Math.sin(a) * 3.1 + Math.sin(t * 0.7 + m.userData.wob) * 0.25
      m.rotation.y += 0.0035
      m.rotation.x = Math.sin(t * 0.5 + m.userData.wob) * 0.22
    })
    camera.position.x += (px * 0.7 - camera.position.x) * 0.03
    camera.position.y += (-py * 0.45 - camera.position.y) * 0.03
    camera.lookAt(0, 0, -2)
    renderer.render(scene, camera)
  }
  loop()

  return {
    dispose() {
      cancelAnimationFrame(raf)
      removeEventListener('pointermove', onPointer)
      renderer.dispose()
      geo.dispose()
      starGeo.dispose()
    },
  }
}
