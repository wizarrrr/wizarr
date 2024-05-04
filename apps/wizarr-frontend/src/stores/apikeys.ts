import type { APIKey, APIKeys } from '@/types/api/apikeys';
import { defineStore } from 'pinia';

interface APIKeyStoreState {
    apikeys: APIKeys;
}

export const useAPIKeyStore = defineStore('apikeys', {
    state: (): APIKeyStoreState => ({
        apikeys: [],
    }),
    actions: {
        async getAPIKeys() {
            const response = await this.$axios
                .get<APIKeys, { data: APIKeys }>('/api/apikeys')
                .catch(() => {
                    this.$toast.error('Could not get API keys');
                    return null;
                });

            if (response !== null) {
                this.updateAPIKeys(response.data);
            }
        },
        updateAPIKeys(newAPIKeys: APIKeys) {
            const newAPIKeyMap = new Map(newAPIKeys.map(key => [key.id, key]));
            const updatedAPIKeys = this.apikeys.map(apikey => newAPIKeyMap.get(apikey.id) || apikey);
            newAPIKeyMap.forEach((apikey, id) => {
                if (!this.apikeys.some(k => k.id === id)) {
                    updatedAPIKeys.push(apikey);
                }
            });
            this.apikeys = updatedAPIKeys.filter(apikey => newAPIKeyMap.has(apikey.id));
        },
        async createAPIKey(apikey: Partial<APIKey>) {
            const formData = new FormData();
            Object.keys(apikey).forEach((key) => {
                // @ts-ignore
                formData.append(key, apikey[key]);
            });
            const response = await this.$axios
                .post('/api/apikeys', formData, { disableErrorToast: true })
                .catch((err) => {
                    this.$toast.error('Could not create API key');
                    console.error(err);
                    return null;
                });

            if (response !== null) {
                this.apikeys.push(response.data as APIKey);
                return response.data as APIKey;
            }
        },
        async deleteAPIKey(id: number) {
            const response = await this.$axios
                .delete(`/api/apikeys/${id}`, { disableInfoToast: true })
                .catch(() => {
                    this.$toast.error('Could not delete API key');
                    return null;
                });

            if (response !== null) {
                this.apikeys = this.apikeys.filter(apikey => apikey.id !== id);
            }
        },
    },
    persist: true,
});
