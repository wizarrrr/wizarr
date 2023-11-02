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
            // Get the API keys from the API
            const apikeys = await this.$axios
                .get<APIKeys, { data: APIKeys }>('/api/apikeys')
                .catch(() => {
                    this.$toast.error('Could not get API keys');
                    return null;
                });

            // If the API keys are null, return
            if (apikeys === null) return;

            // Update the API keys that are already in the store
            this.apikeys.forEach((apikey, index) => {
                const new_apikey = apikeys.data.find(
                    (new_apikey: APIKey) => new_apikey.id === apikey.id,
                );
                if (new_apikey) this.apikeys[index] = new_apikey;
            });

            // Add the new API keys to the store if they don't exist
            apikeys.data.forEach((apikey: APIKey) => {
                if (
                    !this.apikeys.find(
                        (old_apikey) => old_apikey.id === apikey.id,
                    )
                )
                    this.apikeys.push(apikey);
            });

            // Remove the API keys that were not in the response
            this.apikeys.forEach((apikey, index) => {
                if (
                    !apikeys.data.find(
                        (new_apikey: APIKey) => new_apikey.id === apikey.id,
                    )
                )
                    this.apikeys.splice(index, 1);
            });

            // Return the API keys
            return apikeys.data;
        },
        async createAPIKey(apikey: Partial<APIKey>) {
            // Convert the API key to a FormData object
            const formData = new FormData();

            Object.keys(apikey).forEach((key) => {
                // @ts-ignore
                formData.append(key, apikey[key]);
            });

            // Create the API key
            const response = await this.$axios
                .post('/api/apikeys', formData, { disableErrorToast: true })
                .catch((err) => {
                    this.$toast.error('Could not create API key');
                    console.error(err);
                    return null;
                });

            // If the response is null, return
            if (response === null) return;

            // Add the API key to the store
            this.apikeys.push(response.data as APIKey);

            // Return the API key
            return response.data as APIKey;
        },
        async deleteAPIKey(id: number) {
            // Delete the API key from the API
            const response = await this.$axios
                .delete(`/api/apikeys/${id}`, { disableInfoToast: true })
                .catch(() => {
                    this.$toast.error('Could not delete API key');
                    return null;
                });

            // If the response is null, return
            if (response === null) return;

            // Remove the API key from the store
            const index = this.apikeys.findIndex(
                (apikey: APIKey) => apikey.id === id,
            );
            if (index !== -1) this.apikeys.splice(index, 1);
        },
    },
    persist: true,
});
