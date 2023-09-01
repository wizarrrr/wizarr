import { defineStore } from "pinia";
import type { Language } from "vue3-gettext";

export const useLanguageStore = defineStore("language", {
    state: () => ({
        language: "en" as string,
        availableLanguages: {} as { [key: string]: string },
    }),
    actions: {
        setLanguage(language: string) {
            this.language = language;
        },
        updateLanguage(gettext: Language, language: string) {
            gettext.current = language;
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
