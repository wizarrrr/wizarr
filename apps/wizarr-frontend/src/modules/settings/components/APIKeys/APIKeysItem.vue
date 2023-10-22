<template>
    <ListItem icon="fa-key">
        <template #title>
            <div class="flex flex-row space-x-4 w-full">
                <div class="flex flex-col">
                    <span class="text-lg">{{ apikey.name }}</span>
                    <p
                        class="text-xs truncate text-gray-500 dark:text-gray-400 w-full"
                    >
                        {{ $filter('timeAgo', apikey.created) }}
                    </p>
                </div>
            </div>
        </template>
        <template #buttons>
            <div class="flex flex-row space-x-2">
                <FormKit
                    type="button"
                    data-them="secondary"
                    @click="viewKey"
                    :classes="{ input: '!bg-secondary !px-3.5 h-[36px]' }"
                >
                    <i class="fa-solid fa-eye"></i>
                </FormKit>
                <FormKit
                    type="button"
                    data-theme="danger"
                    :disabled="disabled.delete"
                    @click="localDeleteAPIKey"
                    :classes="{ input: '!bg-red-600 !px-3.5 h-[36px]' }"
                >
                    <i class="fa-solid fa-trash"></i>
                </FormKit>
            </div>
        </template>
    </ListItem>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions } from 'pinia';
import { useAPIKeyStore } from '@/stores/apikeys';

import type { APIKey } from '@/types/api/apikeys';

import ListItem from '@/components/ListItem.vue';
import ViewApiKey from '../Modals/ViewApiKey.vue';

export default defineComponent({
    name: 'UserItem',
    components: {
        ListItem,
    },
    props: {
        apikey: {
            type: Object as () => APIKey,
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
        viewKey() {
            const modal_options = {
                title: this.__('View API key'),
            };

            const modal_props = {
                apiKey: this.apikey.key,
            };

            this.$modal.openModal(ViewApiKey, modal_options, modal_props);
        },
        async localDeleteAPIKey() {
            if (
                await this.$modal.confirmModal(
                    this.__('Are you sure?'),
                    this.__('Are you sure you want to delete this API key?'),
                )
            ) {
                this.disabled.delete = true;
                await this.deleteAPIKey(this.apikey.id).finally(
                    () => (this.disabled.delete = false),
                );
                this.$toast.info(this.__('API key deleted successfully'));
            } else {
                this.$toast.info(this.__('API key deletion cancelled'));
            }
        },
        ...mapActions(useAPIKeyStore, ['deleteAPIKey']),
    },
});
</script>
