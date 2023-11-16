import { addons } from "@storybook/manager-api";
import { create } from "@storybook/theming";

const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";

addons.setConfig({
    theme: create({
        base: systemTheme,
        brandTitle: "Wizarr",

        colorPrimary: "#fe4155",
        colorSecondary: "#4B5563",
    }),
});
