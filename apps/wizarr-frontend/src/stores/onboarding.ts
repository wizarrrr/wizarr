import { defineStore } from 'pinia';
import { useServerStore } from "@/stores/server";
import type { FixedOnboardingPage } from '@/types/api/onboarding/FixedOnboardingPage';
import type { OnboardingPage } from '@/types/api/onboarding/OnboardingPage';

export enum FixedOnboardingPageType {
    WelcomePlex = 1,
    DownloadPlex = 2,
    WelcomeJellyfin = 3,
    DownloadJellyfin = 4,
    WelcomeEmby = 5,
    DownloadEmby = 6,
    Request = 7,
}

// Define the shape of the state in this store
interface OnboardingStoreState {
    fixedOnboardingPages: FixedOnboardingPage[];
    onboardingPages: OnboardingPage[];
}

// Define and export a store named 'onboarding' using the Pinia library
export const useOnboardingStore = defineStore('onboarding', {
    // Define the initial state of the store
    state: (): OnboardingStoreState => ({
        fixedOnboardingPages: [],
        onboardingPages: [],
    }),
    getters: {
        enabledOnboardingPages(state) {
            return state.onboardingPages.filter(page => page.enabled);
        },
        enabledFixedOnboardingPages(state) {
            const serverStore = useServerStore();
            const pages = state.fixedOnboardingPages;

            const filteredPages = [];
            if (serverStore.settings.server_type == "plex") {
                const welcomePage = pages.find((page) => page.id === FixedOnboardingPageType.WelcomePlex);
                if(welcomePage) filteredPages.push(welcomePage);
                const downloadPage = pages.find((page) => page.id === FixedOnboardingPageType.DownloadPlex);
                if(downloadPage) filteredPages.push(downloadPage);
            }

            else if (serverStore.settings.server_type == "jellyfin") {
                const welcomePage = pages.find((page) => page.id === FixedOnboardingPageType.WelcomeJellyfin);
                if(welcomePage) filteredPages.push(welcomePage);
                const downloadPage = pages.find((page) => page.id === FixedOnboardingPageType.DownloadJellyfin);
                if(downloadPage) filteredPages.push(downloadPage);
            }

            else if (serverStore.settings.server_type == "emby") {
                const welcomePage = pages.find((page) => page.id === FixedOnboardingPageType.WelcomeEmby);
                if(welcomePage) filteredPages.push(welcomePage);
                const downloadPage = pages.find((page) => page.id === FixedOnboardingPageType.DownloadEmby);
                if(downloadPage) filteredPages.push(downloadPage);
            }

            if (!!serverStore.requests.length) {
                const requestPage = pages.find((page) => page.id === FixedOnboardingPageType.Request);
                if(requestPage) filteredPages.push(requestPage);
            }

            return filteredPages.sort((a, b) => a.id - b.id);
        },
        onboardingVariables: () => {
            const serverStore = useServerStore();
            return {
                "server_name": serverStore.settings.server_name,
                "server_url": serverStore.settings.server_url,
                "server_type": serverStore.settings.server_type,
                "discord_id": serverStore.settings.server_discord_id,
            }
        },
    },
    // Define actions that can mutate the state
    actions: {
        // Asynchronously fetches onboarding pages from the server and updates the state
        async getOnboardingPages() {
            const [fixedOnboardingResponse, onboardingResponse] = await Promise.all([
                this.$axios.get<FixedOnboardingPage, { data: FixedOnboardingPage[] }>('/api/onboarding/fixed'),
                this.$axios.get<OnboardingPage, { data: OnboardingPage[] }>('/api/onboarding')
            ])
                .catch((err) => {
                    this.$toast.error('Could not get onboarding pages');
                    console.error(err);
                    return [{ data: [] }, { data: [] }];
                });
            this.updateFixedOnboardingPages(fixedOnboardingResponse.data);
            this.updateOnboardingPages(onboardingResponse.data);
        },
        // Updates the current onboardingPages state with new data
        updateOnboardingPages(onboardingPages: OnboardingPage[]) {
            const newPageMap = new Map(onboardingPages.map(key => [key.id, key]));
            const updatedPages = this.onboardingPages.map(page => newPageMap.get(page.id) || page);
            newPageMap.forEach((page, id) => {
                if (!this.onboardingPages.some(k => k.id === id)) {
                    updatedPages.push(page);
                }
            });
            this.onboardingPages = updatedPages.filter(page => newPageMap.has(page.id)).sort((a, b) => a.order - b.order);
        },
        // Updates the current fixedOnboardingPages state with new data
        updateFixedOnboardingPages(onboardingPages: FixedOnboardingPage[]) {
            const newPageMap = new Map(onboardingPages.map(key => [key.id, key]));
            const updatedPages = this.onboardingPages.map(page => newPageMap.get(page.id) || page);
            newPageMap.forEach((page, id) => {
                if (!this.onboardingPages.some(k => k.id === id)) {
                    updatedPages.push(page);
                }
            });
            this.fixedOnboardingPages = updatedPages.filter(page => newPageMap.has(page.id)).sort((a, b) => a.id - b.id);
        },
        async updateOnboardingPage(onboardingPage: Pick<OnboardingPage, 'id'> & Partial<OnboardingPage>, fixed = false) {
            const formData = new FormData();
            Object.keys(onboardingPage).forEach((key) => {
                // @ts-ignore
                formData.append(key, onboardingPage[key]);
            });
            await this.$axios
                .put<OnboardingPage>(`/api/onboarding/${fixed ? 'fixed/' : ''}${onboardingPage.id}`, formData, { disableErrorToast: true })
                .catch((err) => {
                    this.$toast.error('Could not update onboarding page');
                    console.error(err);
                    return null;
                });
            await this.getOnboardingPages();
        },
        // Creates a new onboarding page on the server and updates the local state if successful
        async createOnboardingPage(onboardingPage: Partial<OnboardingPage>) {
            const formData = new FormData();
            Object.keys(onboardingPage).forEach((key) => {
                // @ts-ignore
                formData.append(key, onboardingPage[key]);
            });
            const response = await this.$axios
                .post('/api/onboarding', formData, { disableErrorToast: true })
                .catch((err) => {
                    this.$toast.error('Could not create onboarding page');
                    console.error(err);
                    return null;
                });

            if (response !== null) {
                const onboardingPage = response.data.page as OnboardingPage;
                this.updateOnboardingPages([...this.onboardingPages, onboardingPage]);
                return onboardingPage;
            }
        },
        // Deletes an onboarding page from the server and removes it from the local state if successful
        async deleteOnboardingPage(id: number) {
            const response = await this.$axios
                .delete(`/api/onboarding/${id}`, { disableInfoToast: true })
                .catch((err) => {
                    this.$toast.error('Could not delete onboarding page');
                    console.error(err);
                    return null;
                });

            if (response !== null) {
                this.onboardingPages = this.onboardingPages.filter(page => page.id !== id);
            }
        },
    }
});
