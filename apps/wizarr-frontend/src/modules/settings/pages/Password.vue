<template>
    <FormKit type="form" @submit="changePassword" submit-label="Change Password" :actions="false">
        <div class="space-y-4">
            <FormKit type="password" v-model="old_password" label="Old Password" name="old_password" placeholder="Old Password" required autocomplete="current-password" />
            <FormKit type="password" v-model="new_password" label="New Password" name="new_password" placeholder="New Password" required autocomplete="new-password" />
            <PasswordMeter :password="new_password" class="mb-[23px] mt-1 px-[2px]" v-if="new_password" />
            <FormKit type="password" v-model="confirm_password" label="Confirm New Password" name="confirm_password" placeholder="Confirm New Password" required autocomplete="new-password" />

            <div class="">
                <FormKit type="submit" :classes="{ outer: 'w-auto', input: 'text-xs w-auto justify-center !font-bold' }">
                    {{ __("Confirm") }}
                </FormKit>
            </div>
        </div>
    </FormKit>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultNavBar from "@/components/NavBars/DefaultNavBar.vue";
import DefaultLoading from "@/components/Loading/DefaultLoading.vue";

import Auth from "@/api/authentication";
import PasswordMeter from "vue-simple-password-meter";

export default defineComponent({
    name: "LoginView",
    components: {
        DefaultNavBar,
        DefaultLoading,
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
