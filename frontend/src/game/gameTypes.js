export const GAME_TYPES = new Set(['ddz', 'mahjong', 'gomoku', 'xiangqi'])

export function normalizeGameType(game, fallback = 'ddz') {
  return typeof game === 'string' && GAME_TYPES.has(game) ? game : fallback
}
