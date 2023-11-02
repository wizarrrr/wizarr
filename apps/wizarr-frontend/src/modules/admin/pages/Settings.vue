<template>
    <AdminTemplate
        :header="headerText"
        :subheader="subheaderText"
        :box-view="boxView"
    >
        <template #header>
            <div class="relative w-full" v-if="searchBar">
                <div class="hidden md:block">
                    <FormKit
                        id="searchSettings"
                        @input="(value) => (search = value ?? '')"
                        :classes="{
                            input: { 'focus:ring-0': true },
                            outer: { '!mb-0': true },
                        }"
                        type="search"
                        :placeholder="__('Search') + '...'"
                        prefix-icon="fa-search !text-gray-500"
                    />
                </div>
            </div>
            <div class="relative w-full" v-else>
                <DefaultButton
                    to="/admin/settings"
                    icon="fas fa-arrow-left"
                    :options="{ icon: { icon_position: 'left' } }"
                    label="Back"
                />
            </div>
        </template>
        <template #default>
            <RouterView />
        </template>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapState, mapWritableState } from 'pinia';
import { useSettingsStore } from '@/stores/settings';
import { useThemeStore } from '@/stores/theme';

import AdminTemplate from '@/templates/AdminTemplate.vue';
import DefaultButton from '@/components/Buttons/DefaultButton.vue';

export default defineComponent({
    name: 'SettingsView',
    components: {
        AdminTemplate,
        DefaultButton,
    },
    computed: {
        ...mapWritableState(useSettingsStore, ['header', 'search']),
        ...mapState(useThemeStore, ['boxView']),
    },
    data() {
        return {
            headerText: 'Server Settings',
            subheaderText: 'Manage your server settings',
            headerDefault: 'Server Settings',
            subheaderDefault: 'Manage your server settings',
            searchBar: true,
        };
    },
    watch: {
        $route(to) {
            this.searchBar = !!to.meta.searchBar;
            this.headerText = to.meta.header ?? this.headerDefault;
            this.subheaderText = to.meta.subheader ?? this.subheaderDefault;
        },
    },
    mounted() {
        // Show search bar if meta.searchBar is true
        this.searchBar = !!this.$route.meta.searchBar;

        // Set header and subheader text from meta or default
        this.headerText =
            (this.$route?.meta?.header as string) ?? this.headerDefault;
        this.subheaderText =
            (this.$route?.meta?.subheader as string) ?? this.subheaderDefault;
    },
});
</script>
