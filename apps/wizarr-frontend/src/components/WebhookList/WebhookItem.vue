<template>
    <ListItem icon="fa-link">
        <template #title>
            <span class="text-lg">{{ webhook.name }}</span>
            <p class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">
                {{ webhook.url }}
            </p>
            <p class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">
                {{ $filter("timeAgo", webhook.created) }}
            </p>
        </template>
        <template #buttons>
            <div class="flex flex-row space-x-2">
                <!-- <button class="bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-secondary dark:hover:bg-secondary_hover">
                    <i class="fa-solid fa-edit"></i>
                </button> -->
                <button @click="localDeleteWebhook" :disabled="disabled.delete" class="bg-red-600 hover:bg-primary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-red-600 dark:hover:bg-primary_hover">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </template>
    </ListItem>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapActions } from "pinia";
import { useWebhookStore } from "@/stores/webhooks";

import type { Webhook } from "@/types/api/webhooks";

import ListItem from "../ListItem.vue";

export default defineComponent({
    name: "WebhookItem",
    components: {
        ListItem,
    },
    props: {
        webhook: {
            type: Object as () => Webhook,
            required: true,
        },
    },
    data() {
        return {
            disabled: {
                delete: false,
            },
        };
    },
    methods: {
        async localDeleteWebhook() {
            if (await this.$modal.confirmModal(this.__("Are you sure?"), this.__("Are you sure you want to delete this webhook?"))) {
                this.disabled.delete = true;
                await this.deleteWebhook(this.webhook.id).finally(() => (this.disabled.delete = false));
            } else {
                this.$toast.info(this.__("Webhook deletion cancelled"));
            }
        },
        ...mapActions(useWebhookStore, ["deleteWebhook"]),
    },
});
</script>
