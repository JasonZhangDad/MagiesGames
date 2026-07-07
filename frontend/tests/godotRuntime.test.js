import test from 'node:test'
import assert from 'node:assert/strict'

import { countdownSeconds, relativeSeat, seatAtRelative, seatNoAtRelative } from '../src/game/godotRuntime.js'

test('relativeSeat wraps seat indexes around the active anchor', () => {
  assert.equal(relativeSeat(0, 0, 3), 0)
  assert.equal(relativeSeat(1, 0, 3), 1)
  assert.equal(relativeSeat(2, 0, 3), 2)
  assert.equal(relativeSeat(0, 2, 3), 1)
  assert.equal(relativeSeat(1, 2, 3), 2)
})

test('seatNoAtRelative returns the absolute seat for board and table games', () => {
  assert.equal(seatNoAtRelative(2, 1, 3), 0)
  assert.equal(seatNoAtRelative(1, 3, 4), 0)
  assert.equal(seatNoAtRelative(1, 1, 2), 0)
})

test('seatAtRelative reads a seat without mutating the source array', () => {
  const seats = [{ id: 0 }, { id: 1 }, { id: 2 }, { id: 3 }]

  assert.deepEqual(seatAtRelative(seats, 3, 2, 4), { id: 1 })
  assert.deepEqual(seats.map(s => s.id), [0, 1, 2, 3])
})

test('countdownSeconds clamps missing or elapsed deadlines', () => {
  assert.equal(countdownSeconds(null, 100), null)
  assert.equal(countdownSeconds(undefined, 100), null)
  assert.equal(countdownSeconds(96.2, 100), 0)
  assert.equal(countdownSeconds(103.2, 100), 4)
})
