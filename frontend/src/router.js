import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from './api'

const routes = [
  { path: '/', name: 'landing', component: () => import('./views/Landing.vue') },
  { path: '/lobby', name: 'lobby', component: () => import('./views/Lobby.vue') },
  { path: '/game', name: 'game', component: () => import('./views/GameView.vue') },
  { path: '/arcade/:game', name: 'arcade', component: () => import('./views/ArcadeView.vue') },
  { path: '/admin', name: 'admin', component: () => import('./views/Admin.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  if (to.name !== 'landing' && to.name !== 'admin' && !getToken()) return { name: 'landing' }
  return true
})

export default router
