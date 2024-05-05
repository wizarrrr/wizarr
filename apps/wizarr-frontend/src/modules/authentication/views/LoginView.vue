<template>
    <DefaultNavBar />

    <div>
        <div
            class="flex justify-center items-center flex-col mt-12 mb-3 space-y-6"
        >
            <WizarrLogo rounded class="w-[150px] h-[150px]" />
            <h1
                class="text-2xl font-semibold text-center text-gray-900 dark:text-white"
            >
                {{
                    __('Login to the Admin Dashboard')
                }}
            </h1>
        </div>
        <section>
            <div
                class="flex flex-col items-center justify-center md:container py-8 mx-auto"
            >
                <div
                    class="w-full md:w-1/2 lg:w-1/3 bg-white rounded shadow dark:border dark:bg-gray-800 dark:border-gray-700 overflow-hidden"
                >
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
            </div>
        </section>
        <div class="flex justify-center items-center flex-col mb-3 space-y-6">
            <p class="text-sm text-center text-gray-900 dark:text-white">
                {{ __('Made with ❤️ by') }}
                <a
                    class="text-primary font-bold hover:underline"
                    target="_blank"
                    href="https://github.com/wizarrrr/wizarr"
                >
                    Wizarr
                </a>
            </p>
        </div>
    </div>
</template>

<script lang="ts">
import { mapState } from 'pinia';
import { defineComponent } from "vue";
import { useServerStore } from '@/stores/server';

import WizarrLogo from '@/components/WizarrLogo.vue';
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
        WizarrLogo,
    },
    data() {
        return {
            auth: new Auth(),
            step: STEP.LOADING,
            passkeySupported: true,
        };
    },
    computed: {
        ...mapState(useServerStore, ['settings']),
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
