import type { Webhook, Webhooks } from '@/types/api/webhooks';
import { defineStore } from 'pinia';

// Interface defining the state structure for the webhook store
interface WebhookStoreState {
    webhooks: Webhooks;
}

// Define and export a store for handling webhook data
export const useWebhookStore = defineStore('webhooks', {
    // Initial state setup for the store
    state: (): WebhookStoreState => ({
        webhooks: [],
    }),
    // Actions that can be called to manipulate the state
    actions: {
        // Fetches webhooks from the server and updates the state
        async getWebhooks() {
            try {
                const response = await this.$axios.get<Webhook[]>('/api/webhooks');
                if (!response.data) throw new Error('No data received');

                // Create a map of new webhooks for quick lookup
                const newWebhooks = new Map(response.data.map(webhook => [webhook.id, webhook]));

                // Update existing webhooks and filter out any that no longer exist
                this.webhooks = this.webhooks.map(webhook => newWebhooks.get(webhook.id) || webhook)
                                            .filter(webhook => newWebhooks.has(webhook.id));

                // Add new webhooks that are not already in the store
                const existingIds = new Set(this.webhooks.map(webhook => webhook.id));
                response.data.forEach(webhook => {
                    if (!existingIds.has(webhook.id)) {
                        this.webhooks.push(webhook);
                    }
                });
            } catch (error) {
                this.$toast.error('Could not get webhooks'); // Notify user of failure to fetch webhooks
                console.error(error);
            }
        },
        // Creates a new webhook on the server and adds it to the store if successful
        async createWebhook(webhook: Partial<Webhook>) {
            try {
                const formData = new FormData();
                Object.entries(webhook).forEach(([key, value]) => {
                    formData.append(key, value);
                });

                const response = await this.$axios.post<Webhook>('/api/webhooks', formData);
                if (!response.data) throw new Error('Webhook creation failed');

                this.webhooks.push(response.data); // Add the new webhook to the state
                return response.data; // Return the newly created webhook
            } catch (error) {
                this.$toast.error('Could not create webhook'); // Notify user of failure to create webhook
                console.error(error);
            }
        },
        // Deletes a webhook from the server and removes it from the state
        async deleteWebhook(id: number) {
            try {
                await this.$axios.delete(`/api/webhooks/${id}`);
                this.webhooks = this.webhooks.filter(webhook => webhook.id !== id); // Remove the webhook from the state
            } catch (error) {
                this.$toast.error('Could not delete webhook'); // Notify user of failure to delete webhook
                console.error(error);
            }
        },
    },
    persist: true, // Enable persistence for the store to maintain state across sessions
});
