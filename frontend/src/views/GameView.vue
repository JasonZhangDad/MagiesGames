<script setup>
import { computed } from 'vue'
import { useGameStore } from '../stores/game'
import DdzView from './DdzView.vue'
import GomokuView from './GomokuView.vue'
import MahjongView from './MahjongView.vue'
import XiangqiView from './XiangqiView.vue'

const game = useGameStore()
const kind = computed(() => game.room?.game ?? 'ddz')
</script>

<template>
  <MahjongView v-if="kind === 'mahjong'" />
  <GomokuView v-else-if="kind === 'gomoku'" />
  <XiangqiView v-else-if="kind === 'xiangqi'" />
  <DdzView v-else />
</template>
