<template>
    <div class="flex flex-col space-y-4">
        <div v-if="!membership" class="flex flex-col rounded space-y-4" :class="bordered">
            <div class="flex flex-col space-y-2">
                <span class="text-md font-semibold text-gray-900 dark:text-white">{{ __("Login into Membership") }}</span>
                <span class="text-sm text-gray-900 dark:text-white">
                    {{ __("Enter your email and password to login into your membership.") }}
                </span>
            </div>
            <FormKit id="licenseLogin" type="form" :value="loginData" :actions="false" @submit="login" :classes="{ messages: 'hidden' }">
                <div class="flex flex-col space-y-2">
                    <div class="flex flex-col space-y-0">
                        <FormKit name="email" type="email" placeholder="Email" validation="length:5|*email" :classes="{ input: 'w-full justify-center' }" />
                        <FormKit name="password" type="password" placeholder="Password" :classes="{ input: 'w-full justify-center' }" />
                    </div>
                    <div class="flex justify-end space-x-2">
                        <FormKit
                            type="submit"
                            :classes="{
                                input: 'w-full justify-center !py-2.5',
                            }"
                            :disabled="!membership_api">
                            {{ __("Login") }}
                        </FormKit>
                        <FormKit
                            type="button"
                            @click="register"
                            data-theme="transparent"
                            :classes="{
                                input: 'w-full justify-center !py-2.5',
                            }"
                            :disabled="!membership_api">
                            {{ __("Register") }}
                        </FormKit>
                    </div>
                </div>
            </FormKit>
        </div>
        <div v-else class="flex flex-col rounded space-y-4" :class="bordered">
            <div class="flex flex-row justify-between space-x-4">
                <div class="flex flex-col space-y-0">
                    <span class="text-md font-semibold text-gray-900 dark:text-white">{{ __("Membership") }}</span>
                    <span class="text-sm text-gray-900 dark:text-white">{{ __("You are currently logged into membership.") }}</span>
                </div>
                <div class="flex flex-col space-y-0">
                    <span class="text-sm text-gray-900 dark:text-white">{{ membership.email }}</span>
                    <!-- logout -->
                    <FormKit
                        type="button"
                        @click="logout"
                        :classes="{
                            input: '!border-none !py-0 !px-0 !bg-transparent',
                            wrapper: 'flex justify-end',
                        }">
                        {{ __("Logout") }}
                    </FormKit>
                </div>
            </div>

            <hr class="border-gray-200 dark:border-gray-700" />

            <div class="flex flex-col space-y-2">
                <span class="text-sm text-gray-900 dark:text-white">{{ __("Please bare with us while we work on development of this portal.") }}</span>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useThemeStore } from "@/stores/theme";
import { useUserStore } from "@/stores/user";
import { mapState, mapActions } from "pinia";

import Register from "../components/Membership/Register.vue";

export default defineComponent({
    name: "Membership",
    data() {
        return {
            loginData: {
                email: "",
                password: "",
            },
            membership_api: null as string | null,
        };
    },
    computed: {
        bordered() {
            return !this.boxView ? "p-6 border border-gray-200 dark:border-gray-700 rounded" : "";
        },
        ...mapState(useThemeStore, ["boxView"]),
        ...mapState(useUserStore, ["membership"]),
    },
    methods: {
        async login(data: typeof this.loginData) {
            // Send login request to the membership server
            const response = await this.$rawAxios.post(this.membership_api + "/api/login", data).catch((err) => {
                this.$toast.error(err.response.data.message);
            });

            // Verify response has a token
            if (!response?.data?.access_token) return;

            // Save membership token to the database
            await this.$axios.post("/api/membership", {
                token: response.data.access_token,
                email: response.data.user.email,
            });

            // Update membership store and toast
            this.updateMembership({
                token: response.data.access_token,
                email: response.data.user.email,
            });
            this.$toast.info("Successfully logged into membership");
        },
        async register() {
            this.$modal.openModal(Register, {
                title: this.__("Membership Registration"),
                buttons: [
                    {
                        text: this.__("Register"),
                        emit: "register",
                    },
                ],
            });
        },
        async logout() {
            // Send logout request to the membership server
            await this.$axios
                .delete("/api/membership", {
                    disableErrorToast: true,
                    disableInfoToast: true,
                })
                .catch((err) => {
                    this.$toast.error(err.response.data.message);
                });

            // Update membership store and toast
            this.setMembership(null);
            this.$toast.info("Successfully logged out of membership");
        },
        ...mapActions(useUserStore, ["updateMembership", "setMembership"]),
    },
    mounted() {
        this.membership_api = this.$config("membership_api");
    },
});
</script>
