import { defineStore } from 'pinia';
import { useServerStore } from "@/stores/server";
import type { OnboardingPage } from '@/types/api/onboarding/OnboardingPage';

export enum TemplateType {
    Discord = 1,
    Request = 2,
    Download = 3,
}

// Define the shape of the state in this store
interface OnboardingStoreState {
    onboardingPages: OnboardingPage[];
}

// Define and export a store named 'onboarding' using the Pinia library
export const useOnboardingStore = defineStore('onboarding', {
    // Define the initial state of the store
    state: (): OnboardingStoreState => ({
        onboardingPages: [],
    }),
    getters: {
        enabledOnboardingPages(state) {
            return state.onboardingPages.filter(page => page.enabled);
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
            const onboardingResponse = await this.$axios.get<OnboardingPage, { data: OnboardingPage[] }>('/api/onboarding')
                .catch((err) => {
                    this.$toast.error('Could not get onboarding pages');
                    console.error(err);
                    return { data: [] };
                });
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
