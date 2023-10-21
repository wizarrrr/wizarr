import { defineStore } from 'pinia';

interface SettingsStoreState {
    search: string;
    header: 'search' | 'back';
}

export const useSettingsStore = defineStore('settings', {
    state: (): SettingsStoreState => ({
        search: '',
        header: 'search',
    }),
});
