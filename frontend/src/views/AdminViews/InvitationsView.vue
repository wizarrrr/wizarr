<template>
    <AdminTemplate :header="__('Invitations')" :subheader="__('Manage your invitations')">
        <template #header>
            <DefaultButton @click="inviteModal = true" :label="__('Create Invite')" theme="secondary" />
        </template>
        <template #default>
            <InvitationList />
        </template>
    </AdminTemplate>
    <DefaultModal title-string="Create Invite" :visible="inviteModal" @close="inviteModal = false">
        <div class="md:min-w-[400px]">
            <InviteForm />
        </div>
    </DefaultModal>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import AdminTemplate from "@/templates/AdminTemplate.vue";
import DefaultModal from "@/components/Modals/DefaultModal.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";
import InvitationList from "@/components/InvitationList/InvitationList.vue";
import InviteForm from "@/components/Forms/InviteForm.vue";

export default defineComponent({
    name: "InvitationView",
    components: {
        AdminTemplate,
        DefaultModal,
        DefaultButton,
        InvitationList,
        InviteForm,
    },
    data() {
        return {
            inviteModal: false,
        };
    },
});
</script>
