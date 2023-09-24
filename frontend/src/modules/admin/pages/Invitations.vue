<template>
    <AdminTemplate :header="__('Invitations')" :subheader="__('Manage your invitations')" :box-view="boxView">
        <template #header>
            <FormKit type="button" @click="openInviteModal" :classes="{ input: '!bg-secondary' }">
                {{ __("Create Invitation") }}
            </FormKit>
        </template>
        <template #default>
            <InvitationList />
        </template>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState } from "pinia";
import { useThemeStore } from "@/stores/theme";

import AdminTemplate from "@/templates/AdminTemplate.vue";
import InvitationList from "../components/Lists//InvitationList.vue";
import InviteForm from "@/components/Forms/InviteForm.vue";

export default defineComponent({
    name: "InvitationView",
    components: {
        AdminTemplate,
        InvitationList,
        InviteForm,
    },
    data() {
        return {
            inviteModal: false,
        };
    },
    methods: {
        openInviteModal() {
            this.$modal.openModal(InviteForm, {
                title: this.__("Create Invite"),
                disableFooter: true,
            });
        },
    },
    computed: {
        ...mapState(useThemeStore, ["boxView"]),
    },
});
</script>
