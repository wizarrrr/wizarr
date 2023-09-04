/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}", "./node_modules/flowbite/**/*.js", "./src/formkit.theme.ts"],
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
    plugins: [require("flowbite/plugin"), require("tailwindcss-inner-border"), require("@formkit/themes/tailwindcss")],
};
