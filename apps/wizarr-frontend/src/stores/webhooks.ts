import type { Webhook, Webhooks } from '@/types/api/webhooks';
import { defineStore } from 'pinia';

interface WebhookStoreState {
    webhooks: Webhooks;
}

export const useWebhookStore = defineStore('webhooks', {
    state: (): WebhookStoreState => ({
        webhooks: [],
    }),
    actions: {
        async getWebhooks() {
            try {
                const response = await this.$axios.get<Webhook[]>('/api/webhooks');
                if (!response.data) throw new Error('No data received');

                // Create a map of new webhooks for quick lookup
                const newWebhooks = new Map(response.data.map(webhook => [webhook.id, webhook]));

                // Update existing webhooks and filter out any that no longer exist
                this.webhooks = this.webhooks.map(webhook => newWebhooks.get(webhook.id) || webhook).filter(webhook => newWebhooks.has(webhook.id));

                // Add new webhooks that are not already in the store
                const existingIds = new Set(this.webhooks.map(webhook => webhook.id));
                response.data.forEach(webhook => {
                    if (!existingIds.has(webhook.id)) {
                        this.webhooks.push(webhook);
                    }
                });
            } catch (error) {
                this.$toast.error('Could not get webhooks');
                console.error(error);
            }
        },
        async createWebhook(webhook: Partial<Webhook>) {
            try {
                const formData = new FormData();
                Object.entries(webhook).forEach(([key, value]) => {
                    formData.append(key, value);
                });

                const response = await this.$axios.post<Webhook>('/api/webhooks', formData);
                if (!response.data) throw new Error('Webhook creation failed');

                this.webhooks.push(response.data);
                return response.data;
            } catch (error) {
                this.$toast.error('Could not create webhook');
                console.error(error);
            }
        },
        async deleteWebhook(id: number) {
            try {
                await this.$axios.delete(`/api/webhooks/${id}`);
                this.webhooks = this.webhooks.filter(webhook => webhook.id !== id);
            } catch (error) {
                this.$toast.error('Could not delete webhook');
                console.error(error);
            }
        },
    },
    persist: true,
});
