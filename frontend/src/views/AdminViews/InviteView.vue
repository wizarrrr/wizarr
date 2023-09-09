<template>
    <AdminTemplate :header="__('Create Invitation')" :subheader="__('Create an invitation to your server')" class="md:max-w-md">
        <InviteForm />
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import AdminTemplate from "@/templates/AdminTemplate.vue";
import InviteForm from "@/components/Forms/InviteForm.vue";

export default defineComponent({
    name: "InviteView",
    components: {
        AdminTemplate,
        InviteForm,
    },
});
</script>
