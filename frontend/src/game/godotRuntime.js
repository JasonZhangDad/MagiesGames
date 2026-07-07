import { computed, onBeforeUnmount, reactive, ref } from 'vue'

export function relativeSeat(seat, anchor, count) {
  return ((seat - anchor) + count) % count
}

export function seatNoAtRelative(anchor, rel, count) {
  return (anchor + rel) % count
}

export function seatAtRelative(seats, anchor, rel, count) {
  return seats?.[seatNoAtRelative(anchor, rel, count)] ?? null
}

export function countdownSeconds(deadline, nowSeconds) {
  if (!deadline) return null
  return Math.max(0, Math.ceil(deadline - nowSeconds))
}

export function useGodotClock(roomRef, tickMs = 250) {
  const now = ref(Date.now() / 1000)
  const timer = setInterval(() => { now.value = Date.now() / 1000 }, tickMs)
  const countdown = computed(() => countdownSeconds(roomRef.value?.deadline, now.value))

  onBeforeUnmount(() => clearInterval(timer))

  return { now, countdown }
}

export function useGodotSignals(defaultMs = 2400) {
  const bubbles = reactive({})
  const timers = new Set()
  let nextId = 0

  function bubble(seat, text, ms = defaultMs) {
    const id = ++nextId
    bubbles[seat] = { text, id }
    const timer = setTimeout(() => {
      timers.delete(timer)
      if (bubbles[seat]?.id === id) delete bubbles[seat]
    }, ms)
    timers.add(timer)
  }

  function clearBubbles() {
    Object.keys(bubbles).forEach(k => delete bubbles[k])
  }

  onBeforeUnmount(() => {
    timers.forEach(timer => clearTimeout(timer))
    timers.clear()
  })

  return { bubbles, bubble, clearBubbles }
}

export function createSeatRuntime(roomRef, anchorRef, count) {
  const relOf = (seat) => relativeSeat(seat, anchorRef.value, count)
  const seatNoAtRel = (rel) => seatNoAtRelative(anchorRef.value, rel, count)
  const seatAtRel = (rel) => seatAtRelative(roomRef.value?.seats, anchorRef.value, rel, count)

  return { relOf, seatNoAtRel, seatAtRel }
}
