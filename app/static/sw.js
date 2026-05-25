const CACHE_NAME = 'wizarr-v2';
const urlsToCache = [
  '/static/css/main.css',
  '/static/js/dark-mode-switch.js',
  '/static/favicon.ico',
  '/static/wizarr-logo.png',
  '/static/js/vendor/htmx.min.js',
  '/static/js/vendor/alpine.min.js',
  '/static/js/vendor/flowbite.min.js',
  '/static/js/vendor/alpine-collapse.min.js'
];

// Install event - cache resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch event - network-first for HTML pages, cache-first for static assets
self.addEventListener('fetch', (event) => {
  // Always go network-first for HTML page navigation to ensure dynamic Flask backend state works
  if (event.request.mode === 'navigate' || (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html'))) {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }

  // Cache-first for static assets
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});

// Activate event - clean up old caches (effectively busts the old v1 cache)
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Handle background sync and push notifications
self.addEventListener('sync', (event) => {
  console.log('Background sync event:', event);
});

self.addEventListener('push', (event) => {
  console.log('Push event:', event);
}); 