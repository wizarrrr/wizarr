// PWA Service Worker Registration - Prevent double execution
(function() {
  'use strict';

  // Guard against double execution
  if (window.wizarrPWALoaded) {
    return;
  }
  window.wizarrPWALoaded = true;

  // Resolve the worker relative to this script so subpath deployments work.
  var registrationScript = document.currentScript;
  var serviceWorkerUrl = new URL('../sw.js', registrationScript.src);

  // Service Worker Registration
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
      // updateViaCache: 'none' ensures the browser always fetches sw.js from the
      // server instead of the HTTP cache, so service worker updates are detected
      // immediately after deployment.
      navigator.serviceWorker.register(serviceWorkerUrl, { updateViaCache: 'none' })
        .then(function(registration) {
          console.log('ServiceWorker registration successful with scope: ', registration.scope);

          // Check for service worker updates every hour
          setInterval(function() { registration.update(); }, 60 * 60 * 1000);

          // Listen for a new service worker becoming available
          registration.addEventListener('updatefound', function() {
            var newWorker = registration.installing;
            newWorker.addEventListener('statechange', function() {
              if (newWorker.state === 'activated') {
                console.log('New Wizarr version activated');
              }
            });
          });
        })
        .catch(function(err) {
          console.log('ServiceWorker registration failed: ', err);
        });
    });
  }

  // Handle install prompt
  let deferredPrompt;
  window.addEventListener('beforeinstallprompt', function(e) {
    console.log('beforeinstallprompt event fired');
    e.preventDefault();
    deferredPrompt = e;

    // Show install button/banner if needed
    showInstallPromotion();
  });

  function showInstallPromotion() {
    // You can create a custom install button here
    // For now, we'll just log that the app is installable
    console.log('PWA is installable');
  }

  // Handle successful installation
  window.addEventListener('appinstalled', function(e) {
    console.log('PWA was installed');
    deferredPrompt = null;
  });
})();
