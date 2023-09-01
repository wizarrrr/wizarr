<template>
    <form class="space-y-4 md:space-y-6">
        <!-- Server Name -->
        <DefaultInput :class="{ hidden: inputHidden.serverName }" v-model:value="serverNameValue" label="Server Display Name" name="server_name" placeholder="Wizarr" required />

        <!-- Server URL -->
        <DefaultInput :class="{ hidden: inputHidden.serverURL }" v-model:value="serverURLValue" @btnClick="detectServer" :buttonLoading="buttonLoading.detectServer" label="Server URL" name="server_url" placeholder="https://plex.wizarr.dev" size="md" icon="fas fa-arrow-up-right-from-square" button="Detect Server" autocomplete="off" required />

        <!-- Server Type -->
        <SelectInput :class="{ hidden: inputHidden.serverType }" v-model:value="serverTypeValue" disabled label="Server Type" name="server_type" placeholder="Choose a server" size="md" icon="fas fa-server" required>
            <option value="jellyfin">Jellyfin (or Emby)</option>
            <option value="plex">Plex Media Server</option>
        </SelectInput>

        <!-- Server API Key -->
        <DefaultInput :class="{ hidden: inputHidden.serverAPIKey }" v-model:value="serverAPIKeyValue" label="Server API Key" name="server_api_key" placeholder="XXXXXXXXXXXXXXXXX" size="md" icon="fas fa-key" type="off" required />

        <div class="flex flex-col sm:flex-row">
            <!-- Button Group -->
            <div class="flex flex-grow justify-end sm:justify-start space-x-2 mt-2">
                <!-- Scan Servers -->
                <DefaultButton type="button" v-if="!buttonHidden.scanServers" icon="fas fa-search" theme="secondary" :options="{ icon: { icon_position: 'left' } }">
                    <lang>Scan Servers</lang>
                </DefaultButton>

                <!-- Scan Libraries -->
                <DefaultButton type="button" v-if="!buttonHidden.scanLibraries" icon="fas fa-search" :options="{ icon: { icon_position: 'left' } }">
                    <lang>Scan Libraries</lang>
                </DefaultButton>
            </div>

            <div class="flex flex-grow justify-end mt-2 space-x-2">
                <!-- Test Connection -->
                <DefaultButton @click="testConnection" :loading="buttonLoading.testConnection" type="button" v-if="!buttonHidden.testConnection" icon="fas fa-check" :options="{ icon: { icon_position: 'left' } }">
                    <lang>Test Connection</lang>
                </DefaultButton>

                <!-- Save Server -->
                <DefaultButton @click="saveServerSettings" type="button" v-if="!buttonHidden.saveServer" icon="fas fa-save" :options="{ icon: { icon_position: 'left' } }">
                    <lang>Save</lang>
                </DefaultButton>

                <!-- Next Slide -->
                <DefaultButton @click="$emit('nextSlide')" type="button" v-if="!buttonHidden.nextSlide" icon="fas fa-arrow-right">
                    <lang>Next</lang>
                </DefaultButton>
            </div>
        </div>
    </form>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultButton from "@/components/Buttons/DefaultButton.vue";
import DefaultInput from "@/components/Inputs/DefaultInput.vue";
import SelectInput from "@/components/Inputs/SelectInput.vue";

export default defineComponent({
    name: "ServerSettings",
    components: {
        DefaultButton,
        DefaultInput,
        SelectInput,
    },
    props: {
        serverName: {
            type: String,
            default: "",
        },
        serverURL: {
            type: String,
            default: "",
        },
        serverType: {
            type: String,
            default: "",
        },
        serverAPIKey: {
            type: String,
            default: "",
        },
        inputHidden: {
            type: Object,
            default: () => ({
                serverName: false,
                serverURL: false,
                serverType: false,
                serverAPIKey: false,
            }),
        },
        buttonHidden: {
            type: Object,
            default: () => ({
                scanServers: false,
                scanLibraries: false,
                testConnection: false,
                saveServer: false,
                nextSlide: false,
            }),
        },
        buttonLoading: {
            type: Object,
            default: () => ({
                detectServer: false,
                testConnection: false,
            }),
        },
    },
    data() {
        return {
            serverNameValue: this.serverName,
            serverURLValue: this.serverURL,
            serverTypeValue: this.serverType,
            serverAPIKeyValue: this.serverAPIKey,
        };
    },
    methods: {
        detectServer() {
            this.$emit("detectServer", this.serverURLValue);
        },
        testConnection() {
            this.$emit("testConnection", {
                server_name: this.serverNameValue,
                server_url: this.serverURLValue,
                server_type: this.serverTypeValue,
                server_api_key: this.serverAPIKeyValue,
            });
        },
        saveServerSettings() {
            this.$emit("saveServerSettings", {
                server_name: this.serverNameValue,
                server_url: this.serverURLValue,
                server_type: this.serverTypeValue,
                server_api_key: this.serverAPIKeyValue,
            });
        },
    },
    watch: {
        serverName: {
            immediate: false,
            handler(serverName) {
                this.serverNameValue = serverName;
            },
        },
        serverURL: {
            immediate: false,
            handler(serverURL) {
                this.serverURLValue = serverURL;
            },
        },
        serverType: {
            immediate: false,
            handler(serverType) {
                this.serverTypeValue = serverType;
            },
        },
        serverAPIKey: {
            immediate: false,
            handler(serverAPIKey) {
                this.serverAPIKeyValue = serverAPIKey;
            },
        },
    },
});
</script>
