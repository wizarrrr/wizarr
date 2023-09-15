<template>
    <AdminTemplate :header="__('Invited Users')" :subheader="__('Manage your media server users')" :box-view="boxView">
        <template #header>
            <DefaultButton @click="localScanUsers" :loading="buttonWait" :label="__('Scan Users')" icon="fas fa-binoculars" :options="{ icon: { icon_position: 'left' } }" theme="secondary" />
        </template>
        <template #default>
            <UserList />
        </template>
    </AdminTemplate>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useUsersStore } from "@/stores/users";
import { useThemeStore } from "@/stores/theme";
import { mapActions, mapState } from "pinia";

import AdminTemplate from "@/templates/AdminTemplate.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";
import UserList from "@/components/UserList/UserList.vue";

export default defineComponent({
    name: "UsersView",
    components: {
        AdminTemplate,
        DefaultButton,
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
