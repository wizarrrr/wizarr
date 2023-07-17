const tailwindcss = require('tailwindcss');
const autoprefixer = require('autoprefixer');

module.exports = {
    plugins: [
        autoprefixer,
        tailwindcss('./tailwind.config.cjs'), 
    ],
};