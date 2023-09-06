<template>
    <div class="flex flex-wrap items-start md:items-center justify-center mx-auto mt-20 md:mt-0 md:h-screen">
        <!-- Nav Bar for Public Routes -->
        <DefaultNavBar />

        <!-- Hero Section -->
        <section class="flex flex-col items-center justify-center px-6 py-8 mx-auto lg:py-0 w-full">
            <div class="w-full rounded md:mt-0 sm:max-w-md xl:p-0 md:shadow dark:bg-transparent md:bg-white md:dark:border md:dark:border-gray-700">
                <div class="p-6 sm:p-8">
                    <transition name="fade-fast" mode="out-in">
                        <div v-if="step == 0">
                            <DefaultLoading key="loading-screen" />
                        </div>
                        <div v-else-if="step == 1">
                            <UsernameView @submit="submitUsername" v-model:username="username" key="username-form" />
                        </div>
                        <div v-else-if="step == 2">
                            <MFAView @mfaLogin="mfaLogin" @passwordLogin="step = 3" key="mfa-form" />
                        </div>
                        <div v-else-if="step == 3">
                            <PasswordView @passwordLogin="passwordLogin" @mfaLogin="step = 2" :hideMFA="hideMFA" v-model:username="username" v-model:password="password" key="login-form" />
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

import UsernameView from "./UsernameView.vue";
import MFAView from "./MFAView.vue";
import PasswordView from "./PasswordView.vue";

import Auth from "@/api/authentication";

const STEP = {
    LOADING: 0,
    USERNAME: 1,
    MFA: 2,
    PASSWORD: 3,
};

export default defineComponent({
    name: "LoginView",
    components: {
        DefaultNavBar,
        DefaultLoading,
        UsernameView,
        MFAView,
        PasswordView,
    },
    data() {
        return {
            auth: new Auth(),
            step: STEP.LOADING,
            hideMFA: false,
            username: "",
            password: "",
        };
    },
    methods: {
        async submitUsername() {
            const isMFAEnabled = await this.auth.isMFAEnabled(this.username);
            if (isMFAEnabled) this.step = STEP.MFA;
            else (this.step = STEP.PASSWORD) && (this.hideMFA = true);
        },
        async passwordLogin() {
            this.step = STEP.LOADING;
            await this.auth.login(this.username, this.password).catch(() => {
                this.step = STEP.PASSWORD;
            });
        },
        async mfaLogin() {
            this.step = STEP.LOADING;
            await this.auth.mfaAuthentication(this.username).catch((e) => {
                this.$toast.error(e.message);
                this.step = STEP.PASSWORD;
            });
        },
    },
    async mounted() {
        // Check if WebAuthn is supported
        const browserSupportsWebAuthn = this.auth.browserSupportsWebAuthn();
        const browserSupportsWebAuthnAutofill = await this.auth.browserSupportsWebAuthnAutofill();

        // If WebAuthn is not supported go to login with password
        if (!browserSupportsWebAuthn) {
            this.hideMFA = true;
            this.step = STEP.PASSWORD;
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
