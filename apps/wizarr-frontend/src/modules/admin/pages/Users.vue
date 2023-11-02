<template>
    <AdminTemplate :header="__('Invited Users')" :subheader="__('Manage your media server users')" :box-view="boxView">
        <template #header>
            <FormKit id="scanUsers" type="button" :prefix-icon="buttonWait ? 'fa-spinner fa-spin' : 'fa-binoculars'" :disabled="buttonWait" @click="localScanUsers" :classes="{ input: '!bg-secondary' }">
                {{ __("Scan Users") }}
            </FormKit>
        </template>
        <template #default>
            <UserList id="userList" />
        </template>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useUsersStore } from "@/stores/users";
import { useThemeStore } from "@/stores/theme";
import { mapActions, mapState } from "pinia";

import AdminTemplate from "@/templates/AdminTemplate.vue";
import UserList from "../components/Users/UserList/UserList.vue";

export default defineComponent({
    name: "UsersView",
    components: {
        AdminTemplate,
        UserList,
    },
    data() {
        return {
            buttonWait: false,
        };
    },
    methods: {
        async localScanUsers() {
            this.buttonWait = true;
            await this.scanUsers();
            this.buttonWait = false;
        },
        ...mapActions(useUsersStore, ["scanUsers"]),
    },
    computed: {
        ...mapState(useThemeStore, ["boxView"]),
    },
});
</script>
