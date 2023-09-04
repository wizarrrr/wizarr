<template>
    <AdminTemplate :header="header" :subheader="subheader">
        <template #header>
            <div class="relative w-full" v-if="searchBar">
                <div class="hidden md:block">
                    <FormKit @input="(value) => (search = value ?? '')" :classes="{ input: { 'focus:ring-0': true } }" type="search" placeholder="Search..." prefix-icon="fa-search" />
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
