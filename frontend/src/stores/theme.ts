import { defineStore } from "pinia";
import { SYSTEM_VALUE, updateTheme } from "@/assets/ts/utils/DarkMode";
import type { THEME } from "@/assets/ts/utils/DarkMode";

interface ThemeStoreState {
    theme: THEME;
}

export const useThemeStore = defineStore("theme", {
    state: (): ThemeStoreState => ({
        theme: SYSTEM_VALUE,
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
