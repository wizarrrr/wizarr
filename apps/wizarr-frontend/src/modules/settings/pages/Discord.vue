<template>
    <div :class="bordered">
        <div class="flex flex-col space-y-6">
            <div class="flex flex-col space-y-2">
                <div class="flex flex-col space-y-3">
                    <p class="text-sm leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400">
                        {{ __("Configure Wizarr to display a dynamic Discord Widget to users onboarding after signup.") }}
                    </p>
                    <p class="text-xs font-semibold leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400">
                        {{ __("Please enter your Discord Server ID below and ensure Server Widgets are enabled. If you don't know how to get your Discord Server ID or Enable Widgets, please follow the instructions below.") }}
                    </p>
                    <div class="text-sm text-gray-500 dark:text-gray-400 space-y-2">
                        <div class="space-y-1">
                            <p class="text-xs font-semibold leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400">
                                {{ __("Discord Server ID:") }}
                            </p>
                            <ul class="list-decimal pl-8">
                                <li>{{ __("First make sure you have Developer Mode enabled on your Discord by visiting your Discord settings and going to Appearance.") }}</li>
                                <li>{{ __("To get your Server ID right click on the server icon on the left hand sidebar.") }}</li>
                                <li>{{ __('Click on "Copy ID" then paste it it in the box below.') }}</li>
                            </ul>
                        </div>

                        <div class="space-y-1">
                            <p class="text-xs font-semibold leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400">
                                {{ __("Enable Server Widget:") }}
                            </p>
                            <ul class="list-decimal pl-8">
                                <li>{{ __("To enable Server Widgets, navigate to your Server Settings.") }}</li>
                                <li>{{ __('Click "Widget" on the left hand sidebar.') }}</li>
                                <li>{{ __('Ensure the toggle for "Enable Server Widget" is checked.') }}</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            <div class="flex flex-row space-x-2 w-full md:w-1/3 lg:w-1/4">
                <div class="flex-grow">
                    <FormKit type="text" v-model="serverId" v-text="settings.server_discord_id" placeholder="Server ID" :classes="{ input: '!h-[36px] w-full' }" />
                </div>
                <FormKit type="button" @click="saveServerId" :classes="{ input: 'h-[36px]' }">
                    {{ __("Save") }}
                </FormKit>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useThemeStore } from "@/stores/theme";
import { useServerStore } from "@/stores/server";
import { mapState } from "pinia";

export default defineComponent({
    name: "Discord",
    data() {
        return {
            serverId: "",
        };
    },
    methods: {
        async saveServerId() {
            const formData = new FormData();
            formData.append("server_discord_id", this.serverId);

            const validate = await this.$rawAxios.get(`https://discord.com/api/guilds/${this.serverId}/widget.json`).catch((validation) => {
                // Discord Docs: https://discord.com/developers/docs/topics/opcodes-and-status-codes
                if (validation.response.data.code === 50004) {
                    this.$toast.error(this.__("Unable to save due to widgets being disabled on this server."));
                } else if (this.serverId === "") {
                    return Promise.resolve(true); // No server ID, so we can save it
                } else {
                    this.$toast.error(this.__("Unable to save due to an invalid server ID."));
                }
            });

            if (!validate) return;

            const response = await this.$axios.put("/api/settings", formData).catch(() => {
                this.$toast.error(this.__("Unable to save connection."));
                return;
            });

            if (!response?.data) return;

            this.$toast.info("Discord Server ID saved successfully.");
        },
        syncSettings() {
            this.$axios.get("/api/settings", { disableErrorToast: true }).then((response) => {
                if (response.data) this.serverId = response.data.server_discord_id;
            });
        },
    },
    computed: {
        bordered() {
            return !this.boxView ? "border border-gray-200 dark:border-gray-700 rounded-md pt-6 pb-2 px-6" : "";
        },
        ...mapState(useServerStore, ["settings"]),
        ...mapState(useThemeStore, ["boxView"]),
    },
    mounted() {
        this.syncSettings();
    },
});
</script>
