<template>
    <div class="flex flex-col">
        <span class="border border-yellow-500 rounded p-2 text-yellow-500 text-xs text-center">{{ __("This page is currently read only!") }}</span>
        <br />
        <FormKit type="form" :disabled="true" @submit="saveAccount" :submit-label="__('Save Account')" :submit-attrs="{ wrapperClass: 'flex justify-end' }">
            <!-- Name -->
            <div class="flex flex-row flex-wrap gap-2">
                <FormKit type="text" name="firstName" :value="firstName" :label="__('First name')" :placeholder="__('Marvin')" :classes="{ outer: 'flex-grow' }" />
                <FormKit type="text" name="lastName" :value="lastName" :label="__('Last name')" :placeholder="__('Martian')" :classes="{ outer: 'flex-grow' }" />
            </div>

            <!-- Username -->
            <FormKit type="text" name="username" :value="user?.username" :label="__('Username')" :placeholder="__('marvin')" />

            <!-- Email -->
            <FormKit type="email" name="email" :value="user?.email" :label="__('Email')" :placeholder="__('marvin@wizarr.dev')" />
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useUserStore } from "@/stores/user";
import { mapState, mapActions } from "pinia";

interface SaveAccountData {
    firstName: string;
    lastName: string;
    username: string;
    email: string;
}

export default defineComponent({
    name: "AccountView",
    computed: {
        firstName() {
            return this.user?.display_name?.split(" ")[0];
        },
        lastName() {
            return this.user?.display_name?.split(" ")[1];
        },
        ...mapState(useUserStore, ["user"]),
    },
    methods: {
        saveAccount(data: SaveAccountData) {
            this.updateUser({
                display_name: `${data.firstName} ${data.lastName}`,
                username: data.username,
                email: data.email,
            });
        },
        ...mapActions(useUserStore, ["updateUser"]),
    },
});
</script>
