// Owrt MusicBox - Service Worker with Cache-First Strategy
const CACHE_NAME = 'owrt-musicbox-v1';
const STATIC_ASSETS = [
  '/',
  '/static/css/all.min.css',
  '/static/css/style.css',
  '/static/js/script.js',
  '/static/img/default.png',
  '/static/img/favicon.ico',
  '/manifest.json'
];

// Install: cache static assets
self.addEventListener('install', (e) => {
  console.log('[Service Worker] Install');
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (e) => {
  console.log('[Service Worker] Activate');
  e.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names.filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch: cache-first for static, network-first for API
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  
  // Only handle same-origin requests
  if (url.origin !== self.location.origin) {
    e.respondWith(fetch(e.request));
    return;
  }

  // API calls (/status, /control, etc.) - network first
  if (url.pathname.startsWith('/bt/') || 
      url.pathname.startsWith('/control/') || 
      url.pathname.startsWith('/library/') ||
      url.pathname.startsWith('/queue/') ||
      url.pathname === '/status' ||
      url.pathname === '/play' ||
      url.pathname === '/search') {
    e.respondWith(
      fetch(e.request).catch(() => {
        return new Response(JSON.stringify({error: 'offline'}), {
          status: 503,
          headers: {'Content-Type': 'application/json'}
        });
      })
    );
    return;
  }

  // Static assets - cache first
  e.respondWith(
    caches.match(e.request).then((cached) => {
      return cached || fetch(e.request).then((response) => {
        // Cache new assets
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return response;
      });
    })
  );
});