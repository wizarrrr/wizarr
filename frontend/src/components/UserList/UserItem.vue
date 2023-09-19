<template>
    <ListItem>
        <template #icon>
            <div class="flex-shrink-0 h-[60px] w-[60px] rounded bg-gray-50 overflow-hidden">
                <img :src="profilePicture" :onerror="`this.src='${backupPicture}'`" class="w-full h-full object-cover object-center" alt="Profile Picture" />
            </div>
        </template>
        <template #title>
            <span class="text-lg">{{ user.username }}</span>
            <div class="flex flex-col">
                <p v-if="user.email" class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">{{ user.email }}</p>
                <p v-else class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">No email</p>
                <p v-if="user.expires" class="text-xs truncate w-full" :class="color">{{ expired }}</p>
                <p v-else class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">{{ $filter("timeAgo", user.created) }}</p>
            </div>
        </template>
        <template #buttons>
            <div class="flex flex-row space-x-2">
                <button class="bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-secondary dark:hover:bg-secondary_hover">
                    <i class="fa-solid fa-edit"></i>
                </button>
                <button @click="localDeleteUser" :disabled="disabled.delete" class="bg-red-600 hover:bg-primary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-red-600 dark:hover:bg-primary_hover">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </template>
    </ListItem>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapActions } from "pinia";
import { useUsersStore } from "@/stores/users";

import type { User } from "@/types/api/users";

import ListItem from "../ListItem.vue";

export default defineComponent({
    name: "UserItem",
    components: {
        ListItem,
    },
    props: {
        user: {
            type: Object as () => User,
            required: true,
        },
    },
    data() {
        return {
            profilePicture: "https://ui-avatars.com/api/?uppercase=true&name=" + this.user.username + "&length=1",
            backupPicture: "https://ui-avatars.com/api/?uppercase=true&name=" + this.user.username + "&length=1",
            disabled: {
                delete: false,
            },
        };
    },
    computed: {
        expired(): string {
            if (this.$filter("isPast", this.user.expires!)) {
                return this.__("Expired %{s}", { s: this.$filter("timeAgo", this.user.expires!) });
            } else {
                return this.__("Expires %{s}", { s: this.$filter("timeAgo", this.user.expires!) });
            }
        },
        color() {
            const inHalfDay = new Date();
            inHalfDay.setHours(inHalfDay.getHours() + 12);

            if (this.$filter("isPast", this.user.expires!)) {
                return "text-red-600 dark:text-red-500";
            }

            if (this.$filter("dateLess", this.user.expires!, inHalfDay)) {
                return "text-yellow-500 dark:text-yellow-400";
            }

            return "text-gray-500 dark:text-gray-400";
        },
    },
    methods: {
        async getProfilePicture() {
            const response = this.$axios.get(`/api/users/${this.user.token}/profile-picture`, {
                responseType: "blob",
            });

            this.profilePicture = URL.createObjectURL((await response).data);
        },
        async localDeleteUser() {
            if (await this.$modal.confirm(this.__("Are you sure?"), this.__("Do you really want to delete this user from your media server?"))) {
                this.disabled.delete = true;
                await this.deleteUser(this.user.id);
            } else {
                this.disabled.delete = false;
            }
        },
        ...mapActions(useUsersStore, ["deleteUser"]),
    },
    mounted() {
        this.getProfilePicture();
    },
});
</script>
