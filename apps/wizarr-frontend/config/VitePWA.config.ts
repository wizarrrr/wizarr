import type { VitePWAOptions } from "vite-plugin-pwa";

const VitePWAConfig: Partial<VitePWAOptions> = {
    mode: "production",
    base: "/",
    includeAssets: ["favicon.ico"],
    selfDestroying: false,
    srcDir: "src/service",
    filename: "sw.ts",
    registerType: "autoUpdate",
    strategies: "injectManifest",
    workbox: {
        runtimeCaching: [
            {
                handler: "NetworkOnly",
                urlPattern: /\/api\/.*\/*.json/,
                method: "POST",
                options: {
                    backgroundSync: {
                        name: "apiQueue",
                        options: {
                            maxRetentionTime: 24 * 60,
                        },
                    },
                },
            },
        ],
    },
    manifest: {
        name: "Wizarr",
        short_name: "Wizarr",
        theme_color: "#D03143",
        background_color: "#111827",
        orientation: "portrait",
        display: "standalone",
        start_url: "/admin",
        scope: "/",
        description: "Wizarr is an advanced user invitation and management system for Jellyfin, Plex, Emby etc.",
        icons: [
            {
                src: "pwa-192x192.png",
                sizes: "192x192",
                type: "image/png",
            },
            {
                src: "/pwa-512x512.png",
                sizes: "512x512",
                type: "image/png",
            },
            {
                src: "pwa-512x512.png",
                sizes: "512x512",
                type: "image/png",
                purpose: "any maskable",
            },
        ],
    },
    devOptions: {
        enabled: true,
        type: "module",
        navigateFallback: "index.html",
        suppressWarnings: false,
    },
};

export default VitePWAConfig;
