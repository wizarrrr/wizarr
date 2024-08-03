<template>
    <div>
        <!-- Form -->
        <FormKit type="form" id="serverForm" v-model="serverForm" class="space-y-4 md:space-y-6" :actions="false" @submit="saveConnection">
            <!-- Server Name -->
            <FormKit type="text" :label="__('Display Name')" :help="__('Display Name for your media servers')" name="server_name" placeholder="Wizarr" validation="required:trim|alpha_spaces:latin" required autocomplete="text" />

            <!-- Server URL -->
            <FormKit type="inputButton" :label="__('Media Server Address')" :help="__('Server IP or Address of your media server')" name="server_url" validation="required" prefix-icon="fas text-gray-400 fa-arrow-up-right-from-square" placeholder="https://plex.wizarr.dev" @button="detectServer" autocomplete="url" :classes="{ prefixIcon: 'hidden' }">
                {{ __("Detect Server") }}
            </FormKit>

            <!-- Server URL Override -->
            <FormKit type="text" :label="__('Media Server Override')" :help="__('Optional if your server address does not match your external address')" name="server_url_override" placeholder="https://plex.wizarr.dev" validation="trim|url" autocomplete="url" />

            <!-- Server Type -->
            <FormKit type="select" disabled :label="__('Server Type')" :help="__('Detected Media Server')" name="server_type" placeholder="Choose a server" prefix-icon="fas fa-server" :options="serverOptions" validation="required" />

            <!-- Server API Key -->
            <FormKit type="password" :label="__('Server API Key')" :help="__('API key for your media server')" name="server_api_key" prefix-icon="fas text-gray-400 fa-key" placeholder="••••••••" validation="required:trim" required autocomplete="off" />
        </FormKit>

        <!-- Buttons -->
        <div class="flex flex-col sm:flex-row">
            <div class="flex flex-grow justify-end sm:justify-start space-x-2 mt-2">
                <!-- Scan Libraries -->
                <FormKit type="button" v-if="saved || !setup" prefix-icon="fas fa-list" data-theme="secondary" @click="scanLibraries">
                    {{ __("Scan Libraries") }}
                </FormKit>
                <VTooltip>
                    <!-- Scan Servers -->
                    <FormKit type="button" :disabled="true" v-if="!serverForm.server_type || !setup" prefix-icon="fas fa-server" data-theme="secondary" @click="scanServers">
                        {{ __("Scan Servers") }}
                    </FormKit>

                    <template #popper>
                        <span>{{ __("Coming Soon") }}</span>
                    </template>
                </VTooltip>
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
                <FormKit type="button" v-if="saved && setup" suffix-icon="fas fa-arrow-right" @click="$parent!.$emit('nextStep')">
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
    props: {
        setup: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            verified: false,
            saved: false,
            serverForm: {
                server_name: "",
                server_url: "",
                server_url_override: null,
                server_type: "",
                server_api_key: "",
            },
            serverOptions: [
                { label: "Jellyfin", value: "jellyfin" },
                { label: "Emby", value: "emby" },
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
                if (response.data)
                    this.serverForm = {
                        ...this.serverForm,
                        ...response.data,
                    };
            });
        },
        async detectServer() {
            if (!this.serverForm.server_url) return this.$toast.error(this.__("Please enter a server URL."));

            const response = await this.$axios
                .get("/api/utilities/detect-server", {
                    params: { server_url: this.serverForm.server_url },
                })
                .catch(() => {
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

            const response = await this.$axios
                .get("/api/utilities/verify-server", {
                    params: {
                        server_url: this.serverForm.server_url,
                        api_key: this.serverForm.server_api_key,
                    },
                })
                .catch(() => {
                    this.$toast.error(this.__("Unable to verify server."));
                });

            if (!response?.data) return;

            this.verified = true;
            this.$toast.info(this.__("Server connection verified!"));
        },
        async saveConnection() {
            const formData = new FormData();

            // Sanitize server_url and server_url_override to remove trailing slashes
            let server_url = this.serverForm.server_url.trim().replace(/\/$/, "");
            let server_url_override = this.serverForm.server_url_override ? this.serverForm.server_url_override.trim().replace(/\/$/, "") : "";

            // Automatically set server_url_override to https://app.plex.tv if it contains plex.tv, otherwise leave it as is
            server_url_override = server_url_override && server_url_override.includes('plex.tv') ? 'https://app.plex.tv' : server_url_override;

            formData.append("server_name", this.serverForm.server_name);
            formData.append("server_url", server_url);
            formData.append("server_url_override", server_url_override);
            formData.append("server_type", this.serverForm.server_type);
            formData.append("server_api_key", this.serverForm.server_api_key);

            if (!this.setup) {
                const confirm = await this.$modal.confirmModal(this.__("Are you sure?"), this.__("Are you sure you want to save this connection, this will reset your Wizarr instance, which may lead to data loss."));
                if (!confirm) return;
            }

            const response = await this.$axios.put(`/api/settings?setup=${this.setup}`, formData).catch(() => {
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
