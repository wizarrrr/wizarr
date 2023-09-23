<template>
    <ListItem icon="fa-envelope">
        <template #title>
            <button @click="copyLink()" class="text-lg">{{ invite.code }}</button>
            <p v-if="invite.used" class="text-xs truncate w-full" :class="usedColor">{{ __("Invitation used") }}</p>
            <p v-else-if="invite.expires" class="text-xs truncate w-full" :class="expireColor">{{ expired }}</p>
            <p class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">{{ $filter("timeAgo", invite.created) }}</p>
        </template>
        <template #buttons>
            <div class="flex flex-row space-x-2">
                <button class="bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-secondary dark:hover:bg-secondary_hover">
                    <i class="fa-solid fa-edit"></i>
                </button>
                <button :disabled="disabled.delete" @click="deleteLocalInvitation" class="bg-red-600 hover:bg-primary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-red-600 dark:hover:bg-primary_hover">
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
import { useClipboard } from "@vueuse/core";

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
    data() {
        return {
            clipboard: useClipboard(),
            disabled: {
                delete: false,
            },
        };
    },
    methods: {
        async copyLink() {
            await this.clipboard.copy(`${location.origin}/j/${this.invite.code}`);
            this.$toast.info(this.__("Copied to clipboard"));
        },
        async deleteLocalInvitation() {
            if (await this.$modal.confirmModal(this.__("Are you sure?"), this.__("Are you sure you want to delete this invitation?"))) {
                this.disabled.delete = true;
                await this.deleteInvitation(this.invite.id).finally(() => (this.disabled.delete = false));
                this.$toast.info(this.__("Invitation deleted successfully"));
            } else {
                this.$toast.info(this.__("Invitation deletion cancelled"));
            }
        },
        ...mapActions(useInvitationStore, ["deleteInvitation"]),
    },
    computed: {
        expired(): string {
            if (this.$filter("isPast", this.invite.expires)) {
                return this.__("Expired %{s}", { s: this.$filter("timeAgo", this.invite.expires) });
            } else {
                return this.__("Expires %{s}", { s: this.$filter("timeAgo", this.invite.expires) });
            }
        },
        usedColor() {
            if (this.invite.used && this.invite.unlimited) {
                return "text-yellow-500 dark:text-yellow-400";
            }

            if (this.invite.used) {
                return "text-red-600 dark:text-red-500";
            }
        },
        expireColor() {
            const inHalfDay = new Date();
            inHalfDay.setHours(inHalfDay.getHours() + 12);

            if (this.$filter("isPast", this.invite.expires)) {
                return "text-red-600 dark:text-red-500";
            }

            if (this.$filter("dateLess", this.invite.expires, inHalfDay)) {
                return "text-yellow-500 dark:text-yellow-400";
            }

            return "text-gray-500 dark:text-gray-400";
        },
    },
});
</script>
