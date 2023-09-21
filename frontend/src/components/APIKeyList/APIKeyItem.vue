<template>
    <ListItem icon="fa-key">
        <template #title>
            <span class="text-lg">{{ apikey.name }}</span>
            <div class="flex flex-col">
                <!-- <p v-else class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">No email</p> -->
                <p class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">{{ $filter("timeAgo", apikey.created) }}</p>
            </div>
        </template>
        <template #buttons>
            <div class="flex flex-row space-x-2">
                <button @click="localDeleteAPIKey" :disabled="disabled.delete" class="bg-red-600 hover:bg-primary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-red-600 dark:hover:bg-primary_hover">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </template>
    </ListItem>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapActions } from "pinia";
import { useAPIKeyStore } from "@/stores/apikeys";

import type { APIKey } from "@/types/api/apikeys";

import ListItem from "../ListItem.vue";

export default defineComponent({
    name: "UserItem",
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
        async localDeleteAPIKey() {
            if (await this.$modal.confirmModal(this.__("Are you sure?"), this.__("Are you sure you want to delete this API key?"))) {
                this.disabled.delete = true;
                await this.deleteAPIKey(this.apikey.id).finally(() => (this.disabled.delete = false));
                this.$toast.info(this.__("API key deleted successfully"));
            } else {
                this.$toast.info(this.__("API key deletion cancelled"));
            }
        },
        ...mapActions(useAPIKeyStore, ["deleteAPIKey"]),
    },
});
</script>
