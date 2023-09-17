<template>
    <AdminTemplate :header="__('Invitations')" :subheader="__('Manage your invitations')" :box-view="boxView">
        <template #header>
            <FormKit type="button" @click="inviteModal = true" :classes="{ input: '!bg-secondary' }">
                {{ __("Create Invitation") }}
            </FormKit>
        </template>
        <template #default>
            <InvitationList />
        </template>
    </AdminTemplate>
    <DefaultModal title-string="Create Invite" :visible="inviteModal" @close="inviteModal = false" modal-class="md:w-[500px] lg:w-[600px]">
        <div>
            <InviteForm />
        </div>
    </DefaultModal>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState } from "pinia";
import { useThemeStore } from "@/stores/theme";

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
    computed: {
        ...mapState(useThemeStore, ["boxView"]),
    },
});
</script>
