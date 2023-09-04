import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

// Configs
import VitePWAConfig from "./config/VitePWA.config";
import ViteSSRConfig from "./config/ViteSSR.config";

// Plugins
import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";
import ssr from "vite-plugin-ssr/plugin";
import babel from "vite-plugin-babel";
import legacy from "@vitejs/plugin-legacy";
import browserSync from "vite-plugin-browser-sync";
import svgLoader from "vite-svg-loader";

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
            "/api": "http://127.0.0.1:5000",
            "/swaggerui": "http://127.0.0.1:5000",
        },
    },
    // assetsInclude: ["**/*.html"],
});
