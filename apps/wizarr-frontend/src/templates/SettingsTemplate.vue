<template>
    <AdminTemplate :header="header" :subheader="subheader">
        <template #header>
            <div class="relative w-full">
                <div class="hidden md:block">
                    <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                        <i class="fas fa-search text-gray-400"></i>
                    </div>
                    <input v-model="search" type="text" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white" placeholder="Search settings..." />
                </div>
            </div>
            <div class="relative w-full" v-if="backButton">
                <button hx-get="/partials/admin/settings/main" hx-trigger="click" hx-target="#settings-content" hx-swap="innerHTML" hx-push-url="/admin/settings" class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-primary border border-transparent rounded hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-dark">
                    <i class="fas fa-arrow-left"></i>
                    <span class="ml-2">{{ __("Back") }}</span>
                </button>
            </div>
        </template>
        <template #default>
            <slot></slot>
        </template>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapWritableState } from "pinia";
import { useSettingsStore } from "@/stores/settings";

import AdminTemplate from "@/templates/AdminTemplate.vue";

export default defineComponent({
    name: "",
    components: {
        AdminTemplate,
    },
    props: {
        backButton: {
            type: Boolean,
            default: false,
        },
        header: {
            type: String,
            default: "Server Settings",
        },
        subheader: {
            type: String,
            default: "Manage your server settings",
        },
    },
    computed: {
        ...mapWritableState(useSettingsStore, ["search"]),
    },
});
</script>
