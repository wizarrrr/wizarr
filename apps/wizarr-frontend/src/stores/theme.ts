import { SYSTEMMODE, getTheme, updateTheme } from '@/ts/utils/darkMode';

import type { THEME } from '@/ts/utils/darkMode';
import { defineStore } from 'pinia';

interface ThemeStoreState {
    theme: THEME;
    boxView: boolean;
}

export const useThemeStore = defineStore('theme', {
    state: (): ThemeStoreState => ({
        theme: SYSTEMMODE,
        boxView: false,
    }),
    getters: {
        currentTheme: (state) => {
            return getTheme(state.theme);
        },
    },
    actions: {
        updateTheme(theme: THEME) {
            updateTheme(theme);
        },
        toggleTheme() {
            const themeTransitions: Record<THEME, THEME> = {
                dark: 'light',
                light: 'system',
                system: 'dark',
              };
              
            this.theme = themeTransitions[this.theme];
            updateTheme(this.theme);
        },
        getTheme() {
            return getTheme();
        },
    },
    persist: true,
});
