import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ws':  { target: 'ws://127.0.0.1:8000', ws: true },
      // 街机游戏反向代理（HTTP 静态资源 + WebSocket，与生产 Nginx 路由对齐）
      '/arcade/bumper-cars': { target: 'http://127.0.0.1:3001', changeOrigin: true, rewrite: p => p.replace(/^\/arcade\/bumper-cars/, '') },
      '/arcade/neon-fps':    { target: 'http://127.0.0.1:3002', changeOrigin: true, rewrite: p => p.replace(/^\/arcade\/neon-fps/, '') },
      '/arcade/ice-climber': { target: 'http://127.0.0.1:3003', changeOrigin: true, rewrite: p => p.replace(/^\/arcade\/ice-climber/, '') },
      '/arcade/arena-brawl': { target: 'http://127.0.0.1:3004', changeOrigin: true, rewrite: p => p.replace(/^\/arcade\/arena-brawl/, '') },
      '/arcade/bomb-party':  { target: 'http://127.0.0.1:3005', changeOrigin: true, rewrite: p => p.replace(/^\/arcade\/bomb-party/, '') },
    },
  },
  build: {
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: { three: ['three'], vendor: ['vue', 'vue-router', 'pinia', 'gsap'] },
      },
    },
  },
})
