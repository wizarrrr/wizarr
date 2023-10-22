<template>
    <!-- Navbar -->
    <AdminNavBar />

    <!-- Page Content -->
    <div id="content" class="mt-[64px] mb-6">
        <Setttings />
    </div>

    <!-- Footer -->
    <AdminFooter />
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import AdminNavBar from '@/components/NavBars/AdminNavBar.vue';
import AdminFooter from '@/components/Footers/AdminFooter.vue';
import Setttings from '@/modules/admin/pages/Settings.vue';

export default defineComponent({
    name: 'SettingsView',
    components: {
        AdminNavBar,
        AdminFooter,
        Setttings,
    },
});
</script>
