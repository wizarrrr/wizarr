// In-App Browser Escape
// Detects when Wizarr is opened in an in-app browser (e.g., Instagram, Facebook, etc.)
// and provides a way to open the link in the user's default browser

(function() {
  'use strict';

  // Guard against double execution
  if (window.wizarrInAppEscapeLoaded) {
    return;
  }
  window.wizarrInAppEscapeLoaded = true;

  // Import dependencies from node_modules
  const Bowser = window.Bowser;
  const InAppSpy = window.InAppSpy;

  if (!Bowser || !InAppSpy) {
    console.warn('In-app escape dependencies not loaded');
    return;
  }

  // Initialize InAppSpy
  const { isInApp, appKey } = InAppSpy();

  // Get the OS name (lowercase: "ios", "android", etc.)
  const os = Bowser.getParser(window.navigator.userAgent).getOSName(true);

  // Only proceed if we're in an in-app browser
  if (!isInApp) {
    return;
  }

  console.log('In-app browser detected on:', os, 'App:', appKey);

  // Get the current URL
  const currentUrl = window.location.href;

  // Handle Android
  if (os === 'android') {
    // Parse the URL to construct the intent link
    const url = new URL(currentUrl);
    const scheme = url.protocol.replace(':', ''); // 'http' or 'https'
    const host = url.host;
    const path = url.pathname + url.search + url.hash;

    // Create intent link for Android: intent://example.com/path#Intent;scheme=https;end
    const intentLink = `intent://${host}${path}#Intent;scheme=${scheme};end`;

    // Attempt to auto-redirect
    try {
      window.location.replace(intentLink);
    } catch (error) {
      console.warn('Auto-redirect failed, showing manual option:', error);
    }

    // Create a banner with a manual link as fallback
    createEscapeBanner(intentLink, 'android');
  }
  // Handle iOS
  else if (os === 'ios') {
    let escapeLink;

    // Parse URL for web search link
    const url = new URL(currentUrl);

    // Special handling for Snapchat - use web search
    if (appKey === 'snapchat') {
      escapeLink = `x-web-search://?${url.host}`;
      console.log('Using web search escape for Snapchat:', escapeLink);
    } else {
      // For all other in-app browsers, use Safari escape scheme
      escapeLink = currentUrl.replace(/^https?:\/\//, 'x-safari-https://');
      console.log('Using Safari escape:', escapeLink);
    }

    // Attempt to open with the escape link
    try {
      window.location.replace(escapeLink);
    } catch (error) {
      console.warn('Escape attempt failed, showing manual instructions:', error);
    }

    // Show banner with instructions as fallback
    createEscapeBanner(escapeLink, 'ios');
  }
  // Other platforms
  else {
    console.log('In-app browser detected but platform not supported:', os);
  }

  /**
   * Creates a dismissible banner informing the user they're in an in-app browser
   * and providing instructions or a link to open in their default browser
   */
  function createEscapeBanner(link, platform) {
    // Check if banner already exists
    if (document.getElementById('wizarr-inapp-banner')) {
      return;
    }

    // Create banner element
    const banner = document.createElement('div');
    banner.id = 'wizarr-inapp-banner';
    banner.className = 'fixed top-0 left-0 right-0 z-50 p-4 bg-blue-600 dark:bg-blue-700 text-white shadow-lg';
    banner.style.cssText = 'animation: slideDown 0.3s ease-out;';

    // Create banner content based on platform
    let bannerContent = '';

    if (platform === 'android') {
      bannerContent = `
        <div class="max-w-screen-xl mx-auto flex items-start justify-between gap-4">
          <div class="flex-1">
            <p class="text-sm font-medium mb-2">
              You're viewing this in an in-app browser
            </p>
            <p class="text-xs opacity-90 mb-3">
              For the best experience, please open this page in your default browser
            </p>
            <a
              href="${link}"
              target="_blank"
              class="inline-flex items-center px-4 py-2 text-sm font-medium text-blue-600 bg-white rounded-lg hover:bg-gray-100 focus:ring-4 focus:outline-none focus:ring-blue-300"
            >
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
              </svg>
              Open in Browser
            </a>
          </div>
          <button
            onclick="document.getElementById('wizarr-inapp-banner').remove();"
            type="button"
            class="flex-shrink-0 text-white hover:bg-blue-700 dark:hover:bg-blue-800 rounded-lg p-1.5 inline-flex items-center"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
            </svg>
            <span class="sr-only">Close banner</span>
          </button>
        </div>
      `;
    } else if (platform === 'ios') {
      bannerContent = `
        <div class="max-w-screen-xl mx-auto flex items-start justify-between gap-4">
          <div class="flex-1">
            <p class="text-sm font-medium mb-2">
              You're viewing this in an in-app browser
            </p>
            <p class="text-xs opacity-90">
              Tap the <strong>Safari icon</strong> or <strong>Share button</strong> at the bottom of the screen and select "Open in Safari" for the best experience
            </p>
          </div>
          <button
            onclick="document.getElementById('wizarr-inapp-banner').remove();"
            type="button"
            class="flex-shrink-0 text-white hover:bg-blue-700 dark:hover:bg-blue-800 rounded-lg p-1.5 inline-flex items-center"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
            </svg>
            <span class="sr-only">Close banner</span>
          </button>
        </div>
      `;
    }

    banner.innerHTML = bannerContent;

    // Add animation styles
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideDown {
        from {
          transform: translateY(-100%);
          opacity: 0;
        }
        to {
          transform: translateY(0);
          opacity: 1;
        }
      }
    `;
    document.head.appendChild(style);

    // Insert banner at the top of the body
    document.body.insertBefore(banner, document.body.firstChild);

    // Add padding to body to prevent content from being hidden
    const bodyPaddingTop = banner.offsetHeight;
    document.body.style.paddingTop = `${bodyPaddingTop}px`;

    // Remove padding when banner is closed
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.removedNodes.length > 0) {
          mutation.removedNodes.forEach(function(node) {
            if (node.id === 'wizarr-inapp-banner') {
              document.body.style.paddingTop = '';
              observer.disconnect();
            }
          });
        }
      });
    });

    observer.observe(document.body, { childList: true });
  }
})();
