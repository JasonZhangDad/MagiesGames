import test from 'node:test'
import assert from 'node:assert/strict'

import { normalizeGameType } from '../src/game/gameTypes.js'

test('normalizeGameType keeps supported game ids', () => {
  assert.equal(normalizeGameType('ddz'), 'ddz')
  assert.equal(normalizeGameType('mahjong'), 'mahjong')
  assert.equal(normalizeGameType('gomoku'), 'gomoku')
  assert.equal(normalizeGameType('xiangqi'), 'xiangqi')
})

test('normalizeGameType falls back for click events or unknown values', () => {
  assert.equal(normalizeGameType({ type: 'click' }), 'ddz')
  assert.equal(normalizeGameType(undefined), 'ddz')
  assert.equal(normalizeGameType(''), 'ddz')
  assert.equal(normalizeGameType('bad-game'), 'ddz')
})
