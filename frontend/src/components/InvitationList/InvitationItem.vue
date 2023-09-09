<template>
    <ListItem icon="fa-envelope">
        <template #title>
            <span class="text-lg">{{ invite.code }}</span>
            <p class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">{{ expired }}</p>
        </template>
        <template #buttons>
            <div class="flex flex-row space-x-2">
                <button class="bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-secondary dark:hover:bg-secondary_hover">
                    <i class="fa-solid fa-edit"></i>
                </button>
                <button @click="deleteLocalInvitation" class="bg-red-600 hover:bg-primary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-red-600 dark:hover:bg-primary_hover">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </template>
    </ListItem>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useInvitationStore } from "@/stores/invitations";
import { mapActions } from "pinia";

import type { Invitation } from "@/types/api/invitations";

import ListItem from "../ListItem.vue";

export default defineComponent({
    name: "InvitationItem",
    components: {
        ListItem,
    },
    props: {
        invite: {
            type: Object as () => Invitation,
            required: true,
        },
    },
    methods: {
        async deleteLocalInvitation() {
            await this.deleteInvitation(this.invite.id);
        },
        ...mapActions(useInvitationStore, ["deleteInvitation"]),
    },
    computed: {
        expired(): string {
            return (this.$filter("isPast", this.invite.expires) ? this.__("Expires") : this.__("Expired")) + " " + this.$filter("timeAgo", this.invite.expires);
        },
    },
});
</script>
