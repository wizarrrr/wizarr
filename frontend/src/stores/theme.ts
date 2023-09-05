import { defineStore } from "pinia";
import { SYSTEM_VALUE, updateTheme } from "@/assets/ts/utils/DarkMode";
import type { THEME } from "@/assets/ts/utils/DarkMode";

export const useThemeStore = defineStore("theme", {
    state: () => ({
        theme: SYSTEM_VALUE as THEME,
    }),
    getters: {
        currentTheme: (state) => {
            return state.theme;
        },
    },
    actions: {
        updateTheme(theme: THEME) {
            updateTheme(theme);
        },
        toggleTheme() {
            switch (this.theme) {
                case "dark":
                    this.theme = "light";
                    break;
                case "light":
                    this.theme = "system";
                    break;
                case "system":
                    this.theme = "dark";
                    break;
                default:
                    this.theme = "dark";
                    break;
            }

            updateTheme(this.theme);
        },
    },
    persist: true,
});
