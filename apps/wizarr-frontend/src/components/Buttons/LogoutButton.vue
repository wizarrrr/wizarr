<template>
    <VTooltip>
        <button class="text-gray-500 dark:text-gray-400 focus:outline-none text-sm" type="button" @click="logout">
            <div class="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-200 hover:dark:bg-gray-700">
                <i class="fa-solid fa-lg fa-right-from-bracket"></i>
            </div>
        </button>

        <template #popper>
            <span>{{ __("Logout") }}</span>
        </template>
    </VTooltip>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Auth from "@/api/authentication";

export default defineComponent({
    name: "LogoutButton",
    data() {
        return {
            auth: new Auth(),
        };
    },
    methods: {
        async logout() {
            await this.auth.logout();
        },
    },
});
</script>
