<template>
    <div>
        <h1 class="text-xl text-center font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
            {{ __("Restore Backup") }}
        </h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 text-center mt-2">
            {{ __("Restore a backup of your database and configuration from a backup file. You will need to provide the encryption password that was used to create the backup") }}
        </p>
    </div>
    <form class="space-y-4 flex flex-col" @submit.prevent="restoreBackup">
        <!-- Encryption Password -->
        <DefaultInput v-model:value="passwordValue" label="Encryption Password" name="password" type="password" placeholder="Encryption Password" required autocomplete="password" autofocus :restrictions="{ disable_spaces: true }" />

        <!-- Backup File -->
        <input name="backup" class="block w-full mb-5 text-sm text-gray-900 border border-gray-300 rounded cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400" type="file" required accept=".backup" placeholder="Backup File" />

        <!-- Restore Button -->
        <div class="flex justify-end">
            <DefaultButton type="submit" theme="danger" :loading="buttonLoading">
                {{ __("Restore Backup") }}
            </DefaultButton>
        </div>
    </form>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultButton from "@/components/Buttons/DefaultButton.vue";
import DefaultInput from "@/components/Inputs/DefaultInput.vue";

export default defineComponent({
    name: "RestoreView",
    components: {
        DefaultButton,
        DefaultInput,
    },
    data() {
        return {
            passwordValue: "",
            buttonLoading: false,
        };
    },
    methods: {
        async restoreBackup(payload: Event) {
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

            // Show message to the user
            const info = this.$toast.warning("This may take a while, please do not close the page until the process is complete.", { timeout: false, closeButton: false, draggable: false, closeOnClick: false });
            this.$toast.info("A backup of your database will be saved into your database folder.");

            // Get the form data from the payload
            const formData = new FormData(target);

            // Send the request to the server
            await this.$axios.post("/api/backup/restore", formData).catch((error) => {
                // Stop button loading animation
                this.buttonLoading = false;

                // Display an error message
                this.$toast.error("An error occurred while restoring the backup");
                this.$toast.dismiss(info);

                throw new Error("An error occurred while restoring the backup");
            });

            // Show a success message
            this.$toast.info("The backup has been restored");

            target.reset();
            this.$toast.dismiss(info);
            window.location.reload();

            // Stop button loading animation
            this.buttonLoading = false;
        },
    },
});
</script>
