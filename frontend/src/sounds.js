/* WebAudio 合成音效:无外部资源,音量克制。 */
let ctx = null
let muted = localStorage.getItem('mg_mute') === '1'

function ac() {
  if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)()
  if (ctx.state === 'suspended') ctx.resume()
  return ctx
}

function tone(freq, dur = 0.12, type = 'sine', gain = 0.08, when = 0, slide = 0) {
  if (muted) return
  try {
    const c = ac()
    const o = c.createOscillator()
    const g = c.createGain()
    const t = c.currentTime + when
    o.type = type
    o.frequency.setValueAtTime(freq, t)
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(40, freq + slide), t + dur)
    g.gain.setValueAtTime(gain, t)
    g.gain.exponentialRampToValueAtTime(0.001, t + dur)
    o.connect(g).connect(c.destination)
    o.start(t)
    o.stop(t + dur + 0.02)
  } catch { /* 音频不可用时静默 */ }
}

export const sfx = {
  click: () => tone(660, 0.06, 'triangle', 0.05),
  select: () => tone(880, 0.05, 'sine', 0.04),
  deal: () => { for (let i = 0; i < 6; i++) tone(300 + i * 60, 0.05, 'triangle', 0.03, i * 0.05) },
  play: () => tone(520, 0.1, 'triangle', 0.07, 0, -120),
  pass: () => tone(300, 0.1, 'sine', 0.04, 0, -80),
  bomb: () => { tone(120, 0.4, 'sawtooth', 0.12, 0, -60); tone(80, 0.5, 'square', 0.08, 0.05, -30) },
  landlord: () => { tone(523, 0.12, 'triangle', 0.07); tone(659, 0.12, 'triangle', 0.07, 0.1); tone(784, 0.2, 'triangle', 0.08, 0.2) },
  win: () => { [523, 659, 784, 1047].forEach((f, i) => tone(f, 0.18, 'triangle', 0.08, i * 0.12)) },
  lose: () => { [392, 330, 262].forEach((f, i) => tone(f, 0.22, 'sine', 0.06, i * 0.15)) },
  warn: () => tone(980, 0.09, 'square', 0.05),
}

export function isMuted() { return muted }
export function toggleMute() {
  muted = !muted
  localStorage.setItem('mg_mute', muted ? '1' : '0')
  return muted
}
