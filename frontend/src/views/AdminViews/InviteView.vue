<template>
    <AdminTemplate :header="__('Create Invitation')" :subheader="__('Create an invitation to your server')" class="md:max-w-md" :box-view="boxView">
        <div class="md:max-w-md m-auto">
            <InviteForm />
        </div>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState } from "pinia";
import { useThemeStore } from "@/stores/theme";

import AdminTemplate from "@/templates/AdminTemplate.vue";
import InviteForm from "@/components/Forms/InviteForm.vue";

export default defineComponent({
    name: "InviteView",
    components: {
        AdminTemplate,
        InviteForm,
    },
    computed: {
        ...mapState(useThemeStore, ["boxView"]),
    },
});
</script>
