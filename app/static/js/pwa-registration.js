// PWA Service Worker Registration
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/static/sw.js')
      .then(function(registration) {
        console.log('ServiceWorker registration successful with scope: ', registration.scope);
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