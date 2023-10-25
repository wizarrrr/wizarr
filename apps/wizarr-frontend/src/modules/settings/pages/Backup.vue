<template>
    <div class="grid grid-cols-1 md:grid-cols-2">
        <!-- Make Backup -->
        <div class="space-y-4 flex flex-col md:pr-8 border-b border-gray-200 dark:border-gray-700 md:border-0 pb-8 md:pb-0">
            <div class="pb-4 border-b border-gray-200 dark:border-gray-700">
                <h2 class="dark:text-white text-lg font-bold">
                    {{ __("Backup") }}
                </h2>
                <p class="text-sm text-gray-500 dark:text-gray-400 mt-0">
                    {{ __("Create a backup of your database and configuration. Please set an encryption password to protect your backup file.") }}
                </p>
            </div>

            <FormKit
                type="form"
                @submit="createBackup"
                v-model="backupForm"
                submit-label="Create Backup"
                :submit-attrs="{
                    wrapperClass: 'flex justify-end',
                    inputClass: '!bg-secondary',
                }">
                <FormKit type="password" name="password" :label="__('Encryption Password')" :placeholder="__('Password')" validation-visibility="live" validation="required:trim" required autocomplete="none" maxlength="20" :classes="{ outer: backupForm.password ? '!mb-0' : '' }" />
                <PasswordMeter :password="backupForm.password" class="mb-[23px] mt-1 px-[2px]" v-if="backupForm.password" />
            </FormKit>
        </div>

        <!-- Restore Backup -->
        <div class="space-y-4 flex flex-col md:border-l border-gray-200 dark:border-gray-700 md:pl-8 pt-8 md:pt-0">
            <div class="pb-4 border-b border-gray-200 dark:border-gray-700">
                <h2 class="dark:text-white text-lg font-bold">
                    {{ __("Restore") }}
                </h2>
                <p class="text-sm text-gray-500 dark:text-gray-400 mt-0">
                    {{ __("Restore a backup of your database and configuration from a backup file. You will need to provide the encryption password that was used to create the backup.") }}
                </p>
            </div>

            <FormKit
                type="form"
                @submit="restoreBackup"
                v-model="restoreForm"
                submit-label="Restore Backup"
                :submit-attrs="{
                    wrapperClass: 'flex justify-end',
                    inputClass: '!bg-red-600',
                }">
                <FormKit type="password" name="password" :label="__('Encryption Password')" :placeholder="__('Password')" validation="required:trim" required autocomplete="none" maxlength="20" />
                <FormKit type="file" name="backup" :placeholder="__('Backup File')" validation="required" required accept=".backup" />
            </FormKit>
        </div>
    </div>

    <div class="my-3 flex items-center p-4 mb-4 text-yellow-800 border-t-4 border-yellow-300 bg-yellow-50 dark:text-yellow-300 dark:bg-gray-800 dark:border-yellow-800" role="alert">
        <div class="text-sm font-medium space-y-1">
            <p class="text-sm text-gray-500 dark:text-gray-400">
                {{ __("To decrypt and encrypt backup files you can use the tools") }}
                <a href="/admin/settings/backup-debug" class="text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-500">{{ __("here") }}</a
                >.
            </p>
            <p class="text-sm text-gray-500 dark:text-gray-400">
                {{ __("Please bare in mind that these tools are only for debugging purposes and we will not provide you with support from any issues that may arise from using them.") }}
            </p>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapWritableState } from "pinia";
import { useProgressStore } from "@/stores/progress";

import PasswordMeter from "vue-simple-password-meter";

export default defineComponent({
    name: "BackupView",
    components: {
        PasswordMeter,
    },
    data() {
        return {
            backupForm: {
                password: "",
            },
            restoreForm: {
                password: "",
                backup: [] as File[],
            },
        };
    },
    computed: {
        ...mapWritableState(useProgressStore, ["progress", "fullPageLoading"]),
    },
    methods: {
        async createBackup() {
            // Start the loading indicator
            this.progress = true;

            // Create Form Data for API
            const formData = new FormData();
            formData.append("password", this.backupForm.password);

            // Download Backup file from the API
            const response = await this.$axios.post("/api/backup/download", formData, {
                responseType: "blob",
            });

            // Check if the response is an error
            if (response.status != 200) {
                this.progress = false;
                this.$toast.error("An error occurred while creating the backup");
                return;
            }

            // Create a new blob from the response and generate a URL
            const blob = new Blob([response.data], {
                type: "application/octet-stream",
            });
            const url = window.URL.createObjectURL(blob);

            // Get the filename from the response headers
            const filename = response.headers["content-disposition"].split("filename=")[1];

            // Download the file using the generated URL and filename programmatically
            const link = document.createElement("a");
            link.style.display = "none";
            link.href = url;
            link.download = filename;

            // Add the link to the document and click it
            document.body.appendChild(link);
            link.click();

            setTimeout(() => {
                URL.revokeObjectURL(url);
                link.parentNode?.removeChild(link);
            }, 0);

            // Stop the loading indicator
            this.progress = false;
        },
        async restoreBackup() {
            // Start the loading indicator
            this.progress = true;
            this.fullPageLoading = true;

            // Create a file for the form data from the variable
            const file = new File(this.restoreForm.backup, this.restoreForm.backup[0].name);

            // Create Form Data for API
            const formData = new FormData();
            formData.append("password", this.restoreForm.password);
            formData.append("backup", file);

            // Show a message to the user
            const info = this.$toast.warning("This may take a while, please do not close the page until the process is complete.", { timeout: 0 });

            // Send the backup file to the API
            const response = await this.$axios.post("/api/backup/restore", formData).catch(() => {
                this.progress = false;
                this.fullPageLoading = false;
                this.$toast.dismiss(info);
                this.$toast.error("An error occurred while restoring the backup");
                return null;
            });

            // Check if the response is an error
            if (response == null) return;

            // Display a success message
            this.$toast.success("Backup restored successfully");

            // Hide the message
            this.progress = false;
            this.fullPageLoading = false;
        },
    },
});
</script>
