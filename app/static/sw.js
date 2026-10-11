// Minimal Wizarr service worker.
//
// The worker is registered at /static/sw.js, so it controls only /static/.
// It does not cache or intercept requests: the server sends versioned static
// URLs with long cache headers, and the pages and HTMX requests must always
// come from the network. The worker stays so that the PWA install works.
// On activation, it deletes the caches of the old service worker versions.

self.addEventListener('install', () => {
  // Activate the new worker at once, so the old caches go away quickly.
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => Promise.all(
        cacheNames
          .filter((cacheName) => cacheName.startsWith('wizarr-'))
          .map((cacheName) => caches.delete(cacheName))
      ))
      .then(() => self.clients.claim())
  );
});
