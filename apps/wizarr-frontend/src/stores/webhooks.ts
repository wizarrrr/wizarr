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
            // Get webhooks from API
            const webhooks = await this.$axios
                .get<Webhook[], { data: Webhook[] }>('/api/webhooks')
                .catch(() => {
                    this.$toast.error('Could not get webhooks');
                    return null;
                });

            // If the webhooks are null, return
            if (webhooks === null) return;

            // Update the webhooks that are already in the store
            this.webhooks.forEach((webhook, index) => {
                const new_webhook = webhooks.data.find(
                    (new_webhook: Webhook) => new_webhook.id === webhook.id,
                );
                if (new_webhook) this.webhooks[index] = new_webhook;
            });

            // Add the new webhooks to the store if they don't exist
            webhooks.data.forEach((webhook: Webhook) => {
                if (
                    !this.webhooks.find(
                        (old_webhook) => old_webhook.id === webhook.id,
                    )
                )
                    this.webhooks.push(webhook);
            });

            // Remove the webhooks that were not in the response
            this.webhooks.forEach((webhook, index) => {
                if (
                    !webhooks.data.find(
                        (new_webhook: Webhook) => new_webhook.id === webhook.id,
                    )
                )
                    this.webhooks.splice(index, 1);
            });
        },
        async createWebhook(webhook: Partial<Webhook>) {
            // Convert the webhook to a FormData object
            const formData = new FormData();

            Object.keys(webhook).forEach((key) => {
                // @ts-ignore
                formData.append(key, webhook[key]);
            });

            // Create the webhook
            const response = await this.$axios
                .post('/api/webhooks', formData, { disableErrorToast: true })
                .catch((err) => {
                    this.$toast.error('Could not create webhook');
                    console.error(err);
                    return null;
                });

            // If the response is null, return
            if (response === null) return;

            // Add the webhook to the store
            this.webhooks.push(response.data as Webhook);

            // Return the webhook
            return response.data as Webhook;
        },
        async deleteWebhook(id: number) {
            // Delete the webhook from the API
            const response = await this.$axios
                .delete(`/api/webhooks/${id}`, { disableInfoToast: true })
                .catch(() => {
                    this.$toast.error('Could not delete webhook');
                    return null;
                });

            // If the response is null, return
            if (response === null) return;

            // Remove the webhook from the store
            this.webhooks.forEach((webhook, index) => {
                if (webhook.id === id) this.webhooks.splice(index, 1);
            });
        },
    },
    persist: true,
});
