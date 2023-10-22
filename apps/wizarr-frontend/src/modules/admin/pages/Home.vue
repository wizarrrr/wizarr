<template>
    <AdminTemplate
        :header="__('Home')"
        :subheader="__('Manage you Wizarr server')"
        :box-view="boxView"
    >
        <template #header>
            <FormKit
                id="editDashboard"
                type="button"
                @click="isEditing = !isEditing"
                :classes="{ input: buttonClasses }"
            >
                {{ isEditing ? __('Save Dashboard') : __('Edit Dashboard') }}
            </FormKit>
        </template>
        <template #default>
            <Dashboard
                id="welcome"
                :is-editing="isEditing"
                @update:isEditing="isEditing = !isEditing"
            />
        </template>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapState } from 'pinia';
import { useThemeStore } from '@/stores/theme';

import AdminTemplate from '@/templates/AdminTemplate.vue';
import DefaultButton from '@/components/Buttons/DefaultButton.vue';

import Dashboard from '@/components/Dashboard/Dashboard.vue';

export default defineComponent({
    name: 'HomeView',
    components: {
        AdminTemplate,
        DefaultButton,
        Dashboard,
    },
    data() {
        return {
            isEditing: false,
        };
    },
    computed: {
        buttonClasses(): string {
            return this.isEditing ? `!bg-primary` : `!bg-secondary`;
        },
        ...mapState(useThemeStore, ['boxView']),
    },
});
</script>
