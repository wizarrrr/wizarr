<template>
    <MediaForm v-model:serverName="serverNameValue" v-model:serverURL="serverURLValue" v-model:serverType="serverTypeValue" v-model:serverAPIKey="serverAPIKeyValue" :inputHidden="inputHidden" :buttonHidden="buttonHidden" :buttonLoading="buttonLoading" @detectServer="detectServer" @testConnection="testConnection" @saveServer="saveServerSettings" />
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultButton from "@/components/Buttons/DefaultButton.vue";
import DefaultInput from "@/components/Inputs/DefaultInput.vue";
import SelectInput from "@/components/Inputs/SelectInput.vue";

import MediaForm from "../components/Forms/MediaForm.vue";

export default defineComponent({
    name: "MediaServerView",
    components: {
        DefaultButton,
        DefaultInput,
        SelectInput,
        MediaForm,
    },
    props: {
        predefinded: {
            type: String as () => "add" | "edit",
            default: "edit",
        },
    },
    data() {
        return {
            serverNameValue: "Wizarr",
            serverURLValue: "",
            serverTypeValue: "",
            serverAPIKeyValue: "",
            buttonLoading: {
                detectServer: false,
                testConnection: false,
            },
            inputHidden: {
                serverName: false,
                serverURL: false,
                serverType: false,
                serverAPIKey: false,
            },
            buttonHidden: {
                scanServers: false,
                scanLibraries: false,
                testConnection: true,
                saveServer: true,
                nextSlide: true,
            },
            serverDetails: null as null | {
                server_type: string;
                server_url: string;
            },
        };
    },
    async mounted() {
        // Make api calls to get the server data
        const settings = await this.$axios.get("/api/settings");

        // Verify the response is valid
        if (settings.status < 200 || settings.status >= 300) {
            this.$toast.error("Could not retrieve server settings");
        }

        // Get the server details from the response
        const { server_name, server_url, server_type, server_api_key } = settings.data;

        // Set the server details if they exist
        server_name ? (this.serverNameValue = server_name) : null;
        server_url ? (this.serverURLValue = server_url) : null;
        server_type ? (this.serverTypeValue = server_type) : null;
        server_api_key ? (this.serverAPIKeyValue = server_api_key) : null;
    },
    methods: {
        validURL(url: string): boolean {
            try {
                new URL(url);
                return true;
            } catch (e) {
                return false;
            }
        },
        async getServerType(server_url: string): Promise<{ server_type: string; server_url: string }> {
            // Get the server type for the given URL
            const response = await this.$axios.get("/api/utilities/detect-server", {
                params: {
                    server_url,
                },
            });

            // Verify the response is valid
            if (response.status < 200 || response.status >= 300) {
                throw new Error("Invalid response from server");
            }

            // Return the server type
            return response.data;
        },
        async verifyServer(server_url: string, api_key: string): Promise<{ server_type: string; server_url: string }> {
            // Verify the server is valid for the given URL and API key
            const response = await this.$axios.get("/api/utilities/verify-server", {
                params: {
                    server_url,
                    api_key,
                },
            });

            // Verify the response is valid
            if (response.status < 200 || response.status >= 300) {
                throw new Error("Invalid response from server");
            }

            // Return the server type
            return response.data;
        },
        async detectServer(server_url_value: string) {
            // Set the button to loading
            this.buttonLoading.detectServer = true;

            // Verify the URL is valid
            if (!this.validURL(server_url_value)) {
                this.$toast.error("Please enter a valid URL");
                this.buttonLoading.detectServer = false;
                return;
            }

            // Detect the server type for the given URL
            const { server_type, server_url } = await this.getServerType(server_url_value).catch((err) => {
                this.$toast.error(err.message);
                this.buttonLoading.detectServer = false;
                return { server_type: null, server_url: null };
            });

            // Verify the server type and URL are valid
            if (server_type === null || server_url === null) return;

            // Set the server type and URL
            this.serverTypeValue = server_type;
            this.serverURLValue = server_url;

            // Set the server type and URL in the server details
            this.serverDetails = { server_type, server_url };

            // Hide the scan servers button and show the test connection button
            this.buttonHidden.testConnection = false;
            this.buttonHidden.saveServer = true;

            // Set the button to not loading
            this.buttonLoading.detectServer = false;
        },
        async saveServerSettings(server: object) {
            // Get the server details
            const { server_name, server_url, server_type, server_api_key } = server as Partial<{
                server_name: string;
                server_url: string;
                server_type: string;
                server_api_key: string;
            }>;

            // Verify the server details are valid
            if (server_name === undefined || server_url === undefined || server_type === undefined || server_api_key === undefined) {
                this.$toast.error("Please enter valid server details");
                return;
            }

            // Verify the server URL is valid
            if (!this.validURL(server_url)) {
                this.$toast.error("Please enter a valid server URL");
                return;
            }

            // Verify the server type is valid
            if (server_type !== "plex" && server_type !== "jellyfin" && server_type !== "emby") {
                this.$toast.error("Please enter a valid server type");
                return;
            }

            // Create the form data
            const formData = new FormData();
            formData.append("server_name", server_name);
            formData.append("server_url", server_url);
            formData.append("server_type", server_type);
            formData.append("server_api_key", server_api_key);

            // Save the server
            const response = await this.$axios.put("/api/settings", formData);

            // Verify the response is valid
            if (response.status < 200 || response.status >= 300) {
                this.$toast.error("Invalid response from server");
                return;
            }

            // Show success message
            this.$toast.info("Successfully saved media server settings");

            return response.data;
        },
        async testConnection(server: object) {
            // Get the server details
            const { server_name, server_url, server_type, server_api_key } = server as Partial<{
                server_name: string;
                server_url: string;
                server_type: string;
                server_api_key: string;
            }>;

            // Verify the server details are valid
            if (server_name === undefined || server_url === undefined || server_type === undefined || server_api_key === undefined) {
                this.$toast.error("Please enter valid server details");
                return;
            }

            // Set the button to loading
            this.buttonLoading.testConnection = true;

            // Verify the URL is valid
            if (!this.validURL(server_url)) {
                this.$toast.error("Please enter a valid URL");
                this.buttonLoading.testConnection = false;
                return;
            }

            // Verify the server type and URL are valid
            if (this.serverDetails === null) {
                this.$toast.error("Please detect the server first");
                this.buttonLoading.testConnection = false;
                return;
            }

            // Verify the server is valid for the given URL and API key
            const response = await this.verifyServer(server_url, server_api_key).catch((err) => {
                this.$toast.error("Could not verify media server");
                this.buttonLoading.testConnection = false;
                return null;
            });

            // Show message
            this.$toast.info("Successfully connected to media server");

            // Verify the server is valid
            if (response === null) return;

            // Save the server settings
            await this.saveServerSettings(server);

            // Set the button to not loading and hide it
            this.buttonHidden.testConnection = true;
            this.buttonLoading.testConnection = false;
        },
    },
});
</script>
