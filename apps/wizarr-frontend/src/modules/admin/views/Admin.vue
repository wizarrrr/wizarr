<template>
    <!-- Navbar -->
    <AdminNavBar />

    <!-- Page Content -->
    <div id="content" class="mt-[64px] mb-6">
        <RouterView />
    </div>

    <!-- Footer -->
    <AdminFooter />
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import AdminNavBar from '@/components/NavBars/AdminNavBar.vue';
import AdminFooter from '@/components/Footers/AdminFooter.vue';

export default defineComponent({
    name: 'AdminView',
    components: {
        AdminNavBar,
        AdminFooter,
    },
});
</script>
