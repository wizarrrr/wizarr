<template>
    <!-- Navbar -->
    <AdminNavBar />

    <!-- Page Content -->
    <div id="content" class="max-w-screen-xl mx-auto mt-[64px]">
        <Transition name="fade" mode="out-in">
            <RouterView />
        </Transition>
    </div>

    <!-- Footer -->
    <AdminFooter />
</template>

<script lang="ts">
import { defineComponent } from "vue";

import AdminNavBar from "@/components/NavBars/AdminNavBar.vue";
import AdminFooter from "@/components/Footers/AdminFooter.vue";

export default defineComponent({
    name: "AdminView",
    components: {
        AdminNavBar,
        AdminFooter,
    },
});
</script>
