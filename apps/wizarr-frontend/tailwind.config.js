/** @type {import('tailwindcss').Config} */
const { join } = require('path');

export const content = [
    join(__dirname, './index.html'), // main index.html
    join(__dirname, './src/**/*.{vue,js,ts,jsx,tsx}'), // vue components
    join(__dirname, '../../node_modules/flowbite/**/*.js'), // flowbite components
    join(__dirname, './src/formkit.theme.ts'), // formkit theme
    join(__dirname, '../../node_modules/@flavorly/vanilla-components/dist/presets/tailwind/all.json'), // vanilla components
];

export const darkMode = 'class';

export const theme = {
    extend: {
        colors: {
            primary: '#D03143',
            primary_hover: '#cf4858',
            secondary: '#4B5563',
            secondary_hover: '#3d4247',
        },
        animation: {
            wiggle: 'wiggle 0.5s ease-in-out infinite',
            shake: 'shake 0.82s cubic-bezier(.36,.07,.19,.97) both',
        },
        keyframes: {
            wiggle: {
                '0%, 100%': { transform: 'rotate(-0.25deg)' },
                '50%': { transform: 'rotate(0.25deg)' },
            },
            shake: {
                '10%, 90%': { transform: 'translate3d(-1px, 0, 0)' },
                '20%, 80%': { transform: 'translate3d(2px, 0, 0)' },
                '30%, 50%, 70%': { transform: 'translate3d(-4px, 0, 0)' },
                '40%, 60%': { transform: 'translate3d(4px, 0, 0)' },
            },
        },
    },
};

export const plugins = [
    require('flowbite/plugin'), // flowbite
    require('tailwindcss-inner-border'), // inner border
    require('@formkit/themes/tailwindcss'), // formkit
    require('@tailwindcss/forms'), // tailwind forms
    require('tailwind-scrollbar'), // scrollbar
];

export default { content, darkMode, theme, plugins };
