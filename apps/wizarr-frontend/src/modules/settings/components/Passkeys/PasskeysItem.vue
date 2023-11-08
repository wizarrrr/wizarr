<template>
    <ListItem icon="fa-key">
        <template #title>
            <span class="text-lg">{{ mfa.name }}</span>
            <p class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">
                {{ $filter("timeAgo", mfa.created) }}
            </p>
        </template>
        <template #buttons>
            <div class="flex flex-row space-x-2">
                <!-- <button class="bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-secondary dark:hover:bg-secondary_hover">
                    <i class="fa-solid fa-edit"></i>
                </button> -->
                <button @click="deleteLocalMfa" class="bg-red-600 hover:bg-primary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-red-600 dark:hover:bg-primary_hover">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </template>
    </ListItem>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { usePasskeysStore } from "@/stores/passkeys";
import { mapActions } from "pinia";

import type { MFA } from "@/types/api/auth/MFA";

import ListItem from "@/components/ListItem.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

export default defineComponent({
    name: "PasskeysItem",
    components: {
        ListItem,
        DefaultButton,
    },
    props: {
        mfa: {
            type: Object as () => MFA,
            required: true,
        },
    },
    methods: {
        async deleteLocalMfa() {
            await this.deleteMfa(this.mfa.id);
        },
        ...mapActions(usePasskeysStore, ["deleteMfa"]),
    },
});
</script>
