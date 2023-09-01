<template>
    <AdminTemplate :header="header" :subheader="subheader">
        <template #header>
            <div class="relative w-full" v-if="searchBar">
                <div class="hidden md:block">
                    <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                        <i class="fas fa-search text-gray-400"></i>
                    </div>
                    <input v-model="search" type="text" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white" placeholder="Search settings..." />
                </div>
            </div>
            <div class="relative w-full" v-else>
                <DefaultButton to="/admin/settings" icon="fas fa-arrow-left" :options="{ icon: { icon_position: 'left' } }" label="Back" />
            </div>
        </template>
        <template #default>
            <RouterView />
        </template>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapWritableState } from "pinia";
import { useSettingsStore } from "@/stores/settings";

import AdminTemplate from "@/templates/AdminTemplate.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

export default defineComponent({
    name: "SettingsView",
    components: {
        AdminTemplate,
        DefaultButton,
    },
    computed: {
        ...mapWritableState(useSettingsStore, ["header", "search"]),
    },
    data() {
        return {
            header: "Server Settings",
            subheader: "Manage your server settings",
            headerDefault: "Server Settings",
            subheaderDefault: "Manage your server settings",
            searchBar: true,
        };
    },
    watch: {
        $route(to) {
            this.searchBar = !!to.meta.searchBar;
            this.header = to.meta.header ?? this.headerDefault;
            this.subheader = to.meta.subheader ?? this.subheaderDefault;
        },
    },
    mounted() {
        this.searchBar = !!this.$route.meta.searchBar;
    },
});
</script>
