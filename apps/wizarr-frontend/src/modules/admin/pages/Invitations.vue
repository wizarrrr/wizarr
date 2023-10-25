<template>
    <AdminTemplate :header="__('Invitations')" :subheader="__('Manage your invitations')" :box-view="boxView">
        <template #header>
            <FormKit id="createInvitation" type="button" @click="openInviteModal" :classes="{ input: '!bg-secondary' }">
                {{ __("Create Invitation") }}
            </FormKit>
        </template>
        <template #default>
            <InvitationList id="invitationList" />
        </template>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState } from "pinia";
import { useThemeStore } from "@/stores/theme";

import AdminTemplate from "@/templates/AdminTemplate.vue";
import InvitationList from "../components/Invitations/InvitationList/InvitationList.vue";
import InvitationForm from "../components/Forms/InvitationForm.vue";

export default defineComponent({
    name: "InvitationView",
    components: {
        AdminTemplate,
        InvitationList,
        InvitationForm,
    },
    data() {
        return {
            inviteModal: false,
        };
    },
    methods: {
        openInviteModal() {
            this.$modal.openModal(InvitationForm, {
                title: this.__("Create Invitation"),
                buttons: [
                    {
                        text: this.__("Create Invitation"),
                        emit: "createInvitation",
                    },
                ],
            });
        },
    },
    computed: {
        ...mapState(useThemeStore, ["boxView"]),
    },
});
</script>
