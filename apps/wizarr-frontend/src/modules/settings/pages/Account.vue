<template>
    <div class="flex flex-col">
        <div class="mb-4">
            <div class="flex flex-col">
                <div class="text-lg font-bold leading-tight tracking-tight text-gray-900 md:text-xl dark:text-white">Account details</div>
                <div class="text-xs font-semibold leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400">Change email and name</div>
            </div>
        </div>
        <span class="border border-yellow-500 rounded p-2 text-yellow-500 text-xs text-center">{{ __("This section is currently read only!") }}</span>
        <br />
        <FormKit type="form" @submit="saveAccount" :submit-attrs="{ wrapperClass: 'flex justify-end' }" :actions="false">
            <!-- Name -->
            <div class="flex flex-row flex-wrap gap-2">
                <FormKit type="text" name="firstName" :disabled="true" :value="firstName" :label="__('First name')" :placeholder="__('Marvin')" :classes="{ outer: 'flex-grow' }" />
                <FormKit type="text" name="lastName" :disabled="true" :value="lastName" :label="__('Last name')" :placeholder="__('Martian')" :classes="{ outer: 'flex-grow' }" />
            </div>

            <!-- Username -->
            <FormKit type="text" name="username" :disabled="true" :value="user?.username" :label="__('Username')" :placeholder="__('marvin')" />

            <!-- Email -->
            <FormKit type="email" name="email" :disabled="true" :value="user?.email" :label="__('Email')" :placeholder="__('marvin@wizarr.dev')" />

            <div class="flex w-full justify-end">
                <FormKit type="submit" :disabled="true" :classes="{ outer: 'w-auto', input: 'text-xs w-auto justify-center !font-bold' }">
                    {{ __("Save Account") }}
                </FormKit>
            </div>
        </FormKit>
        <div class="py-4 mt-6 border-t border-gray-200 dark:border-gray-600">
            <div class="flex flex-col">
                <div class="text-lg font-bold leading-tight tracking-tight text-gray-900 md:text-xl dark:text-white">Password</div>
                <div class="text-xs font-semibold leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400">Change password</div>
            </div>
        </div>
        <FormKit type="form" @submit="changePassword" submit-label="Change Password" :actions="false">
            <div class="space-y-4">
                <FormKit type="password" v-model="old_password" label="Previous password" name="old_password" placeholder="••••••••" required autocomplete="current-password" />
                <FormKit type="password" v-model="new_password" label="New password" name="new_password" placeholder="••••••••" required autocomplete="new-password" />
                <PasswordMeter :password="new_password" class="mb-[23px] mt-1 px-[2px]" v-if="new_password" />
                <FormKit type="password" v-model="confirm_password" label="Confirm password" name="confirm_password" placeholder="••••••••" required autocomplete="new-password" />

                <div class="flex w-full justify-end">
                    <FormKit type="submit" :classes="{ outer: 'w-auto', input: 'text-xs w-auto justify-center !font-bold' }">
                        {{ __("Change Password") }}
                    </FormKit>
                </div>
            </div>
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useUserStore } from "@/stores/user";
import { mapState, mapActions } from "pinia";

import Auth from "@/api/authentication";
import PasswordMeter from "vue-simple-password-meter";

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
    components: {
        PasswordMeter,
    },
    data() {
        return {
            auth: new Auth(),
            old_password: "",
            new_password: "",
            confirm_password: "",
        };
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
        resetForm() {
            this.old_password = "";
            this.new_password = "";
            this.confirm_password = "";
        },
        async changePassword({ old_password, new_password, confirm_password }: { old_password: string; new_password: string; confirm_password: string }) {
            if (new_password !== confirm_password) {
                this.$toast.error("Passwords do not match");
                return;
            } else if (old_password === new_password) {
                this.$toast.error("New password cannot be the same as the old password");
                return;
            }
            await this.auth.changePassword(old_password, new_password).then((res) => {
                if (res !== undefined) {
                    this.resetForm();
                }
            });
        },
    },
});
</script>
