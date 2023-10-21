import { SYSTEM_VALUE, getTheme, updateTheme } from '@/ts/utils/darkMode';

import type { THEME } from '@/ts/utils/darkMode';
import { defineStore } from 'pinia';

interface ThemeStoreState {
    theme: THEME;
    boxView: boolean;
}

export const useThemeStore = defineStore('theme', {
    state: (): ThemeStoreState => ({
        theme: SYSTEM_VALUE,
        boxView: false,
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
                case 'dark':
                    this.theme = 'light';
                    break;
                case 'light':
                    this.theme = 'system';
                    break;
                case 'system':
                    this.theme = 'dark';
                    break;
                default:
                    this.theme = 'dark';
                    break;
            }

            updateTheme(this.theme);
        },
        getTheme() {
            return getTheme();
        },
    },
    persist: true,
});
