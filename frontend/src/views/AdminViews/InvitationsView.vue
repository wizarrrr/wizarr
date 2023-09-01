<template>
    <AdminTemplate :header="__('Invitations')" :subheader="__('Manage your invitations')">
        <span></span>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import AdminTemplate from "@/templates/AdminTemplate.vue";

export default defineComponent({
    name: "InvitationView",
    components: {
        AdminTemplate,
    },
});
</script>
