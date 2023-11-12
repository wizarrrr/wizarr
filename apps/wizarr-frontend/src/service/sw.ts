/// <reference lib="webworker" />

import { NavigationRoute, registerRoute } from "workbox-routing";
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from "workbox-precaching";

import { clientsClaim } from "workbox-core";

declare let self: ServiceWorkerGlobalScope;

// If in production mode then enable PWA caching
if (import.meta.env.PROD) {
    // self.__WB_MANIFEST is default injection point
    precacheAndRoute(self.__WB_MANIFEST);

    // clean old assets
    cleanupOutdatedCaches();

    let allowlist: undefined | RegExp[];
    if (import.meta.env.DEV) allowlist = [/^\/$/];

    // to allow work offline
    registerRoute(
        new NavigationRoute(createHandlerBoundToURL("index.html"), {
            allowlist,
        }),
    );

    self.skipWaiting();
    clientsClaim();
}
