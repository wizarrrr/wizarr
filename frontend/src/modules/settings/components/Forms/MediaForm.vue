<template>
    <div>
        <!-- Form -->
        <FormKit type="form" id="serverForm" v-model="serverForm" class="space-y-4 md:space-y-6" :actions="false" @submit="saveConnection">
            <!-- Server Name -->
            <FormKit type="text" :label="__('Server Display Name')" name="server_name" placeholder="Wizarr" validation="required:trim|alpha_spaces:latin" required autocomplete="text" />

            <!-- Server URL -->
            <FormKit type="inputButton" :label="__('Server URL')" name="server_url" validation="required" prefix-icon="fas text-gray-400 fa-arrow-up-right-from-square" placeholder="https://plex.wizarr.dev" @button="detectServer" autocomplete="url">
                {{ __("Detect Server") }}
            </FormKit>

            <!-- Server Type -->
            <FormKit type="select" disabled :label="__('Server Type')" name="server_type" placeholder="Choose a server" prefix-icon="fas fa-server" :options="serverOptions" validation="required" />

            <!-- Server API Key -->
            <FormKit type="text" :label="__('Server API Key')" name="server_api_key" prefix-icon="fas text-gray-400 fa-key" placeholder="XXXXXXXXXXXXXXXXX" validation="required:trim" required autocomplete="off" />
        </FormKit>

        <!-- Buttons -->
        <div class="flex flex-col sm:flex-row">
            <div class="flex flex-grow justify-end sm:justify-start space-x-2 mt-2">
                <!-- Scan Libraries -->
                <FormKit type="button" v-if="saved" prefix-icon="fas fa-list" data-theme="secondary" @click="scanLibraries">
                    {{ __("Scan Libraries") }}
                </FormKit>

                <!-- Scan Servers -->
                <FormKit type="button" v-if="!serverForm.server_type" prefix-icon="fas fa-server" data-theme="secondary" @click="scanServers">
                    {{ __("Scan Servers") }}
                </FormKit>
            </div>
            <div class="flex flex-grow justify-end sm:justify-end space-x-2 mt-2">
                <!-- Verify Server -->
                <FormKit type="button" v-if="!verified" :disabled="!serverForm.server_type || !serverForm.server_api_key" @click="verifyConnection">
                    {{ __("Verify Connection") }}
                </FormKit>

                <!-- Save Connection -->
                <FormKit type="button" v-if="verified && !saved" :disabled="!serverForm.server_type || !serverForm.server_api_key" @click="$formkit.submit('serverForm')">
                    {{ __("Save Connection") }}
                </FormKit>

                <!-- Next Button -->
                <FormKit type="button" v-if="saved" suffix-icon="fas fa-arrow-right" @click="$parent!.$emit('nextStep')">
                    {{ __("Next") }}
                </FormKit>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Collapse } from "vue-collapsed";

import ScanLibraries from "../ScanLibraries/ScanLibraries.vue";
import ScanServers from "../ScanServers/ScanServers.vue";

export default defineComponent({
    name: "ServerSettings",
    components: {
        Collapse,
    },
    data() {
        return {
            verified: false,
            saved: false,
            serverForm: {
                server_name: "",
                server_url: "",
                server_type: "",
                server_api_key: "",
            },
            serverOptions: [
                { label: "Jellyfin (or Emby)", value: "jellyfin" },
                { label: "Plex Media Server", value: "plex" },
            ],
        };
    },
    methods: {
        scanLibraries() {
            this.$modal.openModal(ScanLibraries, {
                title: this.__("Scan Libraries"),
                buttons: [
                    {
                        text: this.__("Select Libraries"),
                        emit: "selectLibraries",
                    },
                ],
            });
        },
        scanServers() {
            this.$modal.openModal(ScanServers);
        },
        syncSettings() {
            this.$axios.get("/api/settings", { disableErrorToast: true }).then((response) => {
                if (response.data) this.serverForm = { ...this.serverForm, ...response.data };
            });
        },
        async detectServer() {
            if (!this.serverForm.server_url) return this.$toast.error(this.__("Please enter a server URL."));

            const response = await this.$axios.get("/api/utilities/detect-server", { params: { server_url: this.serverForm.server_url } }).catch(() => {
                this.$toast.error(this.__("Unable to detect server."));
            });

            if (!response?.data) return;

            this.serverForm.server_type = response.data.server_type;
            this.$toast.info(
                this.__("Detected %{server_type} server!", {
                    server_type: response.data.server_type.slice(0, 1).toUpperCase() + response.data.server_type.slice(1),
                }),
            );
        },
        async verifyConnection() {
            if (!this.serverForm.server_url || !this.serverForm.server_api_key) return this.$toast.error(this.__("Please enter a server URL and API key."));

            const response = await this.$axios.get("/api/utilities/verify-server", { params: { server_url: this.serverForm.server_url, api_key: this.serverForm.server_api_key } }).catch(() => {
                this.$toast.error(this.__("Unable to verify server."));
            });

            if (!response?.data) return;

            this.verified = true;
            this.$toast.info(this.__("Server connection verified!"));
        },
        async saveConnection() {
            const formData = new FormData();

            formData.append("server_name", this.serverForm.server_name);
            formData.append("server_url", this.serverForm.server_url);
            formData.append("server_type", this.serverForm.server_type);
            formData.append("server_api_key", this.serverForm.server_api_key);

            const confirm = await this.$modal.confirmModal(this.__("Are you sure?"), this.__("Are you sure you want to save this connection, this will remove the following from your local configuration: <br>- Libraries<br>- Users<br>- Invitations<br>- Request Service<br><br>Disregard this if this is your first setup."));

            if (!confirm) return;

            const response = await this.$axios.put("/api/settings", formData).catch(() => {
                this.$toast.error(this.__("Unable to save connection."));
            });

            if (!response?.data) return;

            this.saved = true;
            this.$toast.info("Connection saved successfully!");
        },
    },
    mounted() {
        this.syncSettings();
    },
});
</script>
