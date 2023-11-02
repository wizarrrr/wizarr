import { defineStore } from 'pinia';

export const useProgressStore = defineStore('progress', {
    state: () => ({
        progress: false as boolean,
        fullPageLoading: true as boolean,
    }),
    actions: {
        startProgress() {
            this.progress = true;
        },
        stopProgress() {
            this.progress = false;
        },
    },
});
