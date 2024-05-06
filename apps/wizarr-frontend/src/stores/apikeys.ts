// Import the types for API keys and the Pinia library function for creating a store
import type { APIKey, APIKeys } from '@/types/api/apikeys';
import { defineStore } from 'pinia';

// Define the shape of the state in this store
interface APIKeyStoreState {
    apikeys: APIKeys;
}

// Define and export a store named 'apikeys' using the Pinia library
export const useAPIKeyStore = defineStore('apikeys', {
    // Define the initial state of the store
    state: (): APIKeyStoreState => ({
        apikeys: [],
    }),
    // Define actions that can mutate the state
    actions: {
        // Asynchronously fetches API keys from the server and updates the state
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
        // Updates the current apikeys state with new data
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
        // Creates a new API key on the server and updates the local state if successful
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
        // Deletes an API key from the server and removes it from the local state if successful
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
    // Persist the state of the store to local storage or another persistence layer
    persist: true,
});
