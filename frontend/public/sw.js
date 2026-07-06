/* Magies 棋牌 Service Worker:壳缓存 + 静态资源 cache-first,API/WS 永不缓存。 */
const VERSION = 'magies-v1'
const SHELL = ['/', '/manifest.webmanifest', '/favicon.svg']

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  if (e.request.method !== 'GET' || url.pathname.startsWith('/api') || url.pathname.startsWith('/ws')) return

  // 页面导航:网络优先,离线兜底壳
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone()
          caches.open(VERSION).then(c => c.put('/', copy))
          return res
        })
        .catch(() => caches.match('/')),
    )
    return
  }

  // 带哈希的静态资源:缓存优先
  if (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/icons/')
      || url.pathname === '/favicon.svg' || url.pathname === '/manifest.webmanifest') {
    e.respondWith(
      caches.match(e.request).then(hit => hit || fetch(e.request).then((res) => {
        const copy = res.clone()
        caches.open(VERSION).then(c => c.put(e.request, copy))
        return res
      })),
    )
  }
})
