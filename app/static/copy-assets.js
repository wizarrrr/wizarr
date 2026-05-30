const fs = require('fs');
const path = require('path');

const assets = [
    // Original assets
    { src: 'node_modules/sortablejs/Sortable.min.js', dest: 'js/sortable.min.js' },
    { src: 'node_modules/tiny-markdown-editor/dist/tiny-mde.min.js', dest: 'js/tiny-mde.min.js' },
    { src: 'node_modules/tiny-markdown-editor/dist/tiny-mde.min.css', dest: 'css/tiny-mde.min.css' },

    // Safe Vendor assets (to fix the White Screen of Death / WAF node_modules blocks)
    { src: 'node_modules/alpinejs/dist/cdn.min.js', dest: 'js/vendor/alpine.min.js' },
    { src: 'node_modules/@alpinejs/collapse/dist/cdn.min.js', dest: 'js/vendor/alpine-collapse.min.js' },
    { src: 'node_modules/flowbite/dist/flowbite.min.js', dest: 'js/vendor/flowbite.min.js' },
    { src: 'node_modules/htmx.org/dist/htmx.min.js', dest: 'js/vendor/htmx.min.js' },
    { src: 'node_modules/htmx-ext-preload/dist/preload.min.js', dest: 'js/vendor/htmx-preload.min.js' },
    { src: 'node_modules/animate.css/animate.min.css', dest: 'css/vendor/animate.min.css' },
    { src: 'node_modules/bowser/bundled.js', dest: 'js/vendor/bowser.min.js' },
    { src: 'node_modules/inapp-spy/dist/index.global.js', dest: 'js/vendor/inapp-spy.min.js' }
];

const isProduction = process.env.NODE_ENV === 'production' || process.env.DOCKER_BUILD === 'true';

console.log('📦 Starting cross-platform asset copy...');

assets.forEach(asset => {
    const srcPath = path.resolve(__dirname, asset.src);
    const destPath = path.resolve(__dirname, asset.dest);

    if (!fs.existsSync(srcPath)) {
        if (isProduction) {
            console.error(`❌ CRITICAL: Source file missing for production build: ${asset.src}`);
            process.exit(1); // Fails the build pipeline safely
        } else {
            console.warn(`⚠️ Warning: Source file not found: ${asset.src}. Skipping in dev mode.`);
            return;
        }
    }

    // Ensure destination directory exists
    const destDir = path.dirname(destPath);
    if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
    }

    try {
        fs.copyFileSync(srcPath, destPath);
        console.log(`✓ Copied ${asset.src} -> ${asset.dest}`);
    } catch (err) {
        console.error(`❌ Failed to copy ${asset.src}:`, err);
        process.exit(1);
    }
});

console.log('✨ All assets copied successfully!');
