<script setup>
import { onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from './stores/game'
import { useUserStore } from './stores/user'
import { socket } from './ws'

const game = useGameStore()
const user = useUserStore()
const router = useRouter()
const route = useRoute()

game.bind()

onMounted(async () => {
  if (user.token) {
    const me = await user.fetchMe()
    if (me) socket.connect(user.token)
  }
})

// 有房间快照 → 进对局页;没有 → 回大厅
watch(() => game.room, (room) => {
  if (room && route.name !== 'game') router.push({ name: 'game' })
  if (!room && route.name === 'game') router.push({ name: 'lobby' })
})
</script>

<template>
  <div class="aurora-bg" />
  <router-view />
  <div class="toasts">
    <div v-for="t in game.toasts" :key="t.id" class="toast" :class="{ err: t.kind === 'err' }">
      {{ t.text }}
    </div>
    <div v-if="game.connStatus === 'reconnecting'" class="toast err">连接断开,正在重连…</div>
  </div>
</template>
