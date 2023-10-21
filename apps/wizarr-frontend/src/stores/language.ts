import type { Language } from 'vue3-gettext';
import { language as autoLanguage } from '@/i18n';
import { defineStore } from 'pinia';

export const useLanguageStore = defineStore('language', {
    state: () => ({
        language: 'auto' as string,
        availableLanguages: {} as { [key: string]: string },
    }),
    actions: {
        setLanguage(language: string) {
            this.language = language;
        },
        updateLanguage(gettext: Language, language: string) {
            gettext.current = language === 'auto' ? autoLanguage : language;
        },
        updateAvailableLanguages(gettext: Language) {
            this.availableLanguages = gettext.available;
        },
        currentLanguage(gettext: Language) {
            return gettext.current;
        },
    },
    persist: true,
});
