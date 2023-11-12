<template>
    <div class="flex flex-wrap items-start md:items-center justify-center mx-auto mt-20 md:mt-0 md:h-screen">
        <!-- Nav Bar for Public Routes -->
        <DefaultNavBar />

        <!-- Hero Section -->
        <section class="flex flex-col items-center justify-center px-6 py-8 mx-auto lg:py-0 w-full">
            <div class="w-full rounded md:mt-0 sm:max-w-md xl:p-0 md:shadow dark:bg-transparent md:bg-white md:dark:border md:dark:border-gray-700">
                <div class="p-6 sm:p-8">
                    <transition name="fade-fast" mode="out-in">
                        <div v-if="step == 0" class="flex flex-col items-center justify-center space-y-4">
                            <i class="fa-solid fa-spinner fa-spin dark:text-white fa-2xl m-4"></i>
                        </div>
                        <div v-else-if="step == 1">
                            <LoginForm :passkeySupported="passkeySupported" @passwordLogin="passwordLogin" @passkeyLogin="passkeyLogin" key="login-form" />
                        </div>
                        <div v-else>
                            <div class="flex flex-col items-center justify-center space-y-4">
                                <span class="text-gray-900 dark:text-white">
                                    {{ __("Something went wrong") }}
                                </span>
                            </div>
                        </div>
                    </transition>
                </div>
            </div>
        </section>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultNavBar from "@/components/NavBars/DefaultNavBar.vue";
import DefaultLoading from "@/components/Loading/DefaultLoading.vue";

import LoginForm from "../components/LoginForm.vue";

import Auth from "@/api/authentication";

const STEP = {
    LOADING: 0,
    USERNAME: 1,
};

export default defineComponent({
    name: "LoginView",
    components: {
        DefaultNavBar,
        DefaultLoading,
        LoginForm,
    },
    data() {
        return {
            auth: new Auth(),
            step: STEP.LOADING,
            passkeySupported: true,
        };
    },
    methods: {
        async passwordLogin({ username, password }: { username: string; password: string }) {
            this.step = STEP.LOADING;
            await this.auth.login(username, password).catch(() => {
                this.step = STEP.USERNAME;
            });
        },
        async passkeyLogin({ username }: { username: string }) {
            this.step = STEP.LOADING;
            await this.auth.mfaAuthentication(username).catch((e) => {
                this.$toast.error(e.message);
                this.step = STEP.USERNAME;
            });
        },
    },
    async mounted() {
        // Check if WebAuthn is supported
        const browserSupportsWebAuthn = this.auth.browserSupportsWebAuthn();
        const browserSupportsWebAuthnAutofill = await this.auth.browserSupportsWebAuthnAutofill();

        // If WebAuthn is not supported go to login with password
        if (!browserSupportsWebAuthn) {
            this.step = STEP.USERNAME;
            this.passkeySupported = false;
            return;
        }

        // Remove loading screen
        this.step = STEP.USERNAME;

        // Wait 500ms
        await new Promise((resolve) => setTimeout(resolve, 500));

        // If WebAuthn autofill is supported, allow user to login with MFA autofill
        if (browserSupportsWebAuthn && browserSupportsWebAuthnAutofill) {
            this.auth.mfaAuthentication("", true);
        }
    },
});
</script>
