const CACHE_NAME = 'wizarr-v1';
const urlsToCache = [
  '/',
  '/static/css/main.css',
  '/static/js/dark-mode-switch.js',
  '/static/favicon.ico',
  '/static/wizarr-logo.png',
  '/static/node_modules/htmx.org/dist/htmx.min.js',
  '/static/node_modules/alpinejs/dist/cdn.min.js',
  '/static/node_modules/flowbite/dist/flowbite.min.js',
  '/static/node_modules/@alpinejs/collapse/dist/cdn.min.js'
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

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Handle background sync and push notifications (optional)
self.addEventListener('sync', (event) => {
  console.log('Background sync event:', event);
});

self.addEventListener('push', (event) => {
  console.log('Push event:', event);
}); 