<template>
    <AdminTemplate :header="__('Invited Users')" :subheader="__('Manage your media server users')">
        <span></span>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import AdminTemplate from "@/templates/AdminTemplate.vue";

export default defineComponent({
    name: "UsersView",
    components: {
        AdminTemplate,
    },
});
</script>
