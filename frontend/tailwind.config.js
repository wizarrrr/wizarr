/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./index.html", // main index.html
        "./src/**/*.{vue,js,ts,jsx,tsx}", // vue components
        "./node_modules/flowbite/**/*.js", // flowbite components
        "./src/formkit.theme.ts", // formkit theme
        "./node_modules/@flavorly/vanilla-components/dist/presets/tailwind/all.json", // vanilla components
    ],
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                primary: "#fe4155",
                primary_hover: "#e05362",
                secondary: "#4B5563",
                secondary_hover: "#39414b",
            },
        },
    },
    plugins: [
        require("flowbite/plugin"), // flowbite
        require("tailwindcss-inner-border"), // inner border
        require("@formkit/themes/tailwindcss"), // formkit
        require("@tailwindcss/forms"), // tailwind forms
    ],
};
