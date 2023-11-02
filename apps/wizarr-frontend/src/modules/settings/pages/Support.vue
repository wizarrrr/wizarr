<template>
    <div class="flex flex-col space-y-4" :class="bordered">
        <div class="flex flex-col space-y-1">
            <span class="text-md font-semibold text-gray-900 dark:text-white">{{ __("Live Support") }}</span>
            <p class="text-gray-500 dark:text-gray-300">
                {{ __("We're here to help you with any issues or questions you may have. If you require assistance, paying members can use the button below to begin a live support session with a Wizarr assistant and we will attempt to guide you through any issues you may be having and resolve them.") }}
            </p>
        </div>
        <hr class="border-gray-200 dark:border-gray-700" />
        <FormKit type="button" @click="startSupportSession" :disabled="!livechat_api" :classes="{ wrapper: 'flex justify-end' }">
            {{ __("Start Support Session") }}
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useThemeStore } from "@/stores/theme";
import { useUserStore } from "@/stores/user";
import { mapState } from "pinia";

import jwtDecode from "jwt-decode";
import type { ToastID } from "vue-toastification/dist/types/types";

export default defineComponent({
    name: "Support",
    data() {
        return {
            livechat_api: this.$config("livechat_api"),
            valid_membership: false,
            session_toast: null as ToastID | null,
        };
    },
    computed: {
        bordered() {
            return !this.boxView ? "p-6 border border-gray-200 dark:border-gray-700 rounded" : "";
        },
        ...mapState(useThemeStore, ["boxView"]),
        ...mapState(useUserStore, ["user", "membership"]),
    },
    watch: {
        membership: {
            immediate: true,
            handler(membership) {
                this.valid_membership = membership?.token ? jwtDecode(membership.token) : false;
            },
            deep: true,
        },
    },
    methods: {
        sessionFinished(support: any) {
            support.closeWidget();
            document.querySelector(".rocketchat-widget")?.remove();
            if (this.session_toast) this.$toast.dismiss(this.session_toast);
            this.session_toast = this.$toast.info(this.__("Support session ended"));
        },
        async startSupportSession() {
            // Check if membership is valid
            if (!this.valid_membership) {
                // Warn user that they need to be a paying member to use this feature
                await this.$modal.confirmModal(this.__("Membership Required"), this.__("You must be a paying member to use this feature."), {
                    confirmButtonText: this.__("Okay"),
                    disableCancelButton: true,
                });

                // Redirect to membership page
                this.$router.push("/admin/settings/membership");

                // Don't continue
                return;
            }

            // Confirm with user that they wish to start a support session
            const confirm = await this.$modal.confirmModal(this.__("Start Support Session"), this.__("Are you sure you want to start a support session?"), { confirmButtonText: this.__("Yes") });

            // If user doesn't confirm, don't continue
            if (!confirm) return;

            // Redirect to support page
            const support = new this.$RocketChat(this.livechat_api);

            if (this.env.NODE_ENV === "development") {
                console.table({
                    name: this.user?.display_name,
                    email: this.user?.email,
                    token: this.membership?.token,
                });
            }

            // Set guest details
            if (this.user?.display_name) support.setGuestName(this.user.display_name);
            if (this.user?.email) support.setGuestEmail(this.user.email);
            if (this.membership?.token) support.setGuestToken(this.membership.token);

            // Open support session
            support.maximizeWidget();
            support.onChatEnded(() => this.sessionFinished(support));
            support.onOfflineFormSubmit(() => this.sessionFinished(support));
            support.onChatMinimized(() => this.sessionFinished(support));
        },
    },
});
</script>
