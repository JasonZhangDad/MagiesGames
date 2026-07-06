<script setup>
import { computed } from 'vue'
import { useGameStore } from '../stores/game'
import DdzView from './DdzView.vue'
import MahjongView from './MahjongView.vue'

const game = useGameStore()
const kind = computed(() => game.room?.game ?? 'ddz')
</script>

<template>
  <MahjongView v-if="kind === 'mahjong'" />
  <DdzView v-else />
</template>
