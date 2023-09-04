<template>
    <AdminTemplate header="Test View" subheader="This is a test view.">
        <template #title>
            <h1 class="text-2xl font-semibold text-gray-900">Test View</h1>
        </template>
        <template #default>
            <div class="p-4">
                <FormKit type="search" placeholder="Search..." value="Apple Cider" />
            </div>
        </template>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import AdminTemplate from "@/templates/AdminTemplate.vue";

export default defineComponent({
    name: "TestView",
    components: {
        AdminTemplate,
    },
});
</script>
