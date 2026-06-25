const CACHE_NAME = 'wizarr-v2';
const urlsToCache = [
  'css/main.css',
  'js/dark-mode-switch.js',
  'favicon.ico',
  'wizarr-logo.png',
  'js/vendor/htmx.min.js',
  'js/vendor/alpine.min.js',
  'js/vendor/flowbite.min.js',
  'js/vendor/alpine-collapse.min.js'
].map((path) => new URL(path, self.location.href).href);

// Install event - cache resources and activate immediately
self.addEventListener('install', (event) => {
  // Skip waiting so the new service worker activates immediately,
  // ensuring users with stale caches get the fix without closing all tabs.
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache:', CACHE_NAME);
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch event - network-first for HTML pages, stale-while-revalidate for static assets
self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Network-first for HTML page navigation to ensure dynamic Flask backend state works
  if (event.request.mode === 'navigate' || (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html'))) {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }

  // Stale-while-revalidate for static assets:
  // Serve from cache immediately for speed, but fetch a fresh copy in the
  // background so the next load always has the latest version.
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.match(event.request).then((cachedResponse) => {
        const fetchPromise = fetch(event.request).then((networkResponse) => {
          // Only cache successful responses from our own origin
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            cache.put(event.request, networkResponse.clone());
          }
          return networkResponse;
        }).catch(() => {
          // Network failed, cachedResponse (if any) is already being returned
        });
        if (cachedResponse) {
          // Keep the service worker alive to complete the background fetch and cache update
          event.waitUntil(fetchPromise);
          return cachedResponse;
        }
        return fetchPromise;
      });
    })
  );
});

// Activate event - clean up old caches and claim all open clients immediately
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
    // Claim all open clients so the new service worker takes control immediately,
    // without requiring a page reload.
    .then(() => self.clients.claim())
  );
});

// Handle background sync and push notifications
self.addEventListener('sync', (event) => {
  console.log('Background sync event:', event);
});

self.addEventListener('push', (event) => {
  console.log('Push event:', event);
});
