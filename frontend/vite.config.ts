import { URL, fileURLToPath } from "node:url";

import { VitePWA } from "vite-plugin-pwa";
// Configs
import VitePWAConfig from "./config/VitePWA.config";
import ViteSSRConfig from "./config/ViteSSR.config";
import babel from "vite-plugin-babel";
import browserSync from "vite-plugin-browser-sync";
import { defineConfig } from "vite";
import legacy from "@vitejs/plugin-legacy";
import ssr from "vite-plugin-ssr/plugin";
import svgLoader from "vite-svg-loader";
// Plugins
import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        vue(), // Initizalize Vue Plugin
        vueJsx(), // Initialize Vue JSX Plugin
        // ssr(ViteSSRConfig), // Initialize Vite SSR Plugin (Disabled for now)
        VitePWA(VitePWAConfig), // Initialize Vite PWA Plugin
        babel(), // Initialize Babel Plugin
        // legacy(), // Initialize Legacy Plugin
        // browserSync(), // Initialize BrowserSync Plugin
        svgLoader(), // Initialize SVG Loader Plugin
    ],
    build: {
        sourcemap: true,
    },
    resolve: {
        alias: {
            "@": fileURLToPath(new URL("./src", import.meta.url)),
        },
    },
    server: {
        proxy: {
            "/api": {
                target: "http://127.0.0.1:5000",
                changeOrigin: true,
                xfwd: true,
            },
            "/swaggerui": {
                target: "http://127.0.0.1:5000",
                changeOrigin: true,
                xfwd: true,
            },
            "/socket.io": {
                target: "ws://127.0.0.1:5000",
                changeOrigin: true,
                ws: true,
                xfwd: true,
            },
        },
    },
    // assetsInclude: ["**/*.html"],
});
