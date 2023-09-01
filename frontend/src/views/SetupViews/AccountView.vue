<template>
    <h1 class="text-xl text-center font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
        {{ __("Admin Account") }}
    </h1>
    <div>
        <form class="space-y-4 md:space-y-6" @submit.prevent="createAccount">
            <!-- Display Name -->
            <DefaultInput label="Display Name" type="text" name="display_name" placeholder="Marvin Brown" required autocomplete="name" />

            <!-- Username -->
            <DefaultInput label="Username" type="text" name="username" placeholder="marvin" required autocomplete="username" :restrictions="{ alpha_numeric: true }" />

            <!-- Email -->
            <DefaultInput label="Email" type="email" name="email" placeholder="marvin@wizarr.dev" required autocomplete="email" />

            <!-- Password -->
            <DefaultInput label="Password" type="password" name="password" placeholder="••••••••" required autocomplete="new-password" :password-meter="true" />

            <!-- Confirm Password -->
            <DefaultInput label="Confirm Password" type="password" name="confirm_password" placeholder="••••••••" required autocomplete="new-password" />

            <div class="flex justify-end">
                <DefaultButton type="submit" ref="submitBtn" :loading="buttonLoading">
                    {{ __("Create account") }}
                </DefaultButton>
            </div>
        </form>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultInput from "@/components/Inputs/DefaultInput.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";
import DefaultToast from "@/components/Toasts/DefaultToast.vue";

export default defineComponent({
    name: "AdminAccount",
    components: {
        DefaultInput,
        DefaultButton,
    },
    data() {
        return {
            buttonLoading: false,
        };
    },
    methods: {
        async createAccount(payload: Event) {
            // Start button loading animation and get target
            this.buttonLoading = true;
            const target = payload.target as HTMLFormElement | null;

            // Make sure the target exists
            if (!target) {
                // Stop button loading animation
                this.buttonLoading = false;

                // Display an error message
                this.$toast.error("An error occurred while restoring the backup");

                // Stop the function
                return;
            }

            // Check that the passwords match
            const password = target.password.value;
            const confirmPassword = target.confirm_password.value;

            // If the passwords do not match, display an error
            if (password != confirmPassword) {
                this.$toast.error("Passwords do not match");
                this.buttonLoading = false;
                return;
            }

            // Get the form data from the payload
            const formData = new FormData(target);

            // Send request to API to create admin account
            await this.$axios.post("/api/setup/accounts", formData).catch(() => {
                // Stop button loading animation
                this.buttonLoading = false;

                // Display an error message
                this.$toast.error(DefaultToast("Account Error", "Failed to create admin account"));

                // Throw the error
                throw new Error("Failed to create admin account");
            });

            // Show a success message
            this.$toast.info("The admin account has been created");

            // Go to next step
            this.$emit("nextSlide", { accounts: true });
        },
    },
});
</script>
