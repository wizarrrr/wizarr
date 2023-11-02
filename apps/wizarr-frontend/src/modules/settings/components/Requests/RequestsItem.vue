<template>
    <ListItem :svg-string="icon">
        <template #title>
            <span class="text-lg">{{ request.name }}</span>
            <p class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">
                {{ $filter("timeAgo", request.created) }}
            </p>
        </template>
        <template #buttons>
            <div class="flex flex-row space-x-2">
                <!-- Edit Button -->
                <FormKit type="button" data-theme="secondary" :disabled="true" :classes="{ input: '!bg-secondary !px-3.5 h-[36px]' }">
                    <i class="fa-solid fa-edit"></i>
                </FormKit>
                <FormKit type="button" data-theme="danger" :disabled="disabled.delete" @click="localDeleteAPIKey" :classes="{ input: '!bg-red-600 !px-3.5 h-[36px]' }">
                    <i class="fa-solid fa-trash"></i>
                </FormKit>
            </div>
        </template>
    </ListItem>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useRequestsStore } from "@/stores/requests";
import { mapActions } from "pinia";

import ListItem from "@/components/ListItem.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

export default defineComponent({
    name: "RequestsItem",
    components: {
        ListItem,
        DefaultButton,
    },
    props: {
        request: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            disabled: {
                delete: false,
            },
            icon: "",
        };
    },
    methods: {
        ...mapActions(useRequestsStore, ["deleteRequest"]),
        async localDeleteAPIKey() {
            this.disabled.delete = true;
            this.$modal.confirmModal(this.__("Are you sure?"), this.__("Are you sure you want to delete this request?")).then(async (result) => {
                if (result) await this.deleteRequest(this.request.id);
                this.disabled.delete = false;
            });
        },
    },
    async beforeCreate() {
        const icon = await import(`../../../../assets/img/logo/${this.request.service}.svg?raw`);
        this.icon = icon.default;
    },
});
</script>
