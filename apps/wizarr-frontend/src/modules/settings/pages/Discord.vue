<template>
    <div :class="bordered">
        <div class="flex flex-col space-y-6">
            <div class="flex flex-col space-y-2">
                <p class="text-sm leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400">
                    {{ __("Configure Wizarr to display a dynamic Discord Widget to users onboarding the wizard after signup.") }}
                </p>
                <div class="flex flex-col space-y-1">
                    <p class="text-xs font-semibold leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400">
                        {{ __("Please enter your Discord Server ID below. If you don't know how to get your Discord Server ID, please follow the instructions below.") }}
                    </p>
                    <p class="text-sm text-gray-500 dark:text-gray-400">
                        <li>{{ __("First make sure you have Developer Mode enabled on your Discord by visiting your Discord settings and going to Appearance.") }}</li>
                        <li>{{ __("To get your Server ID right click on the server icon on the left hand sidebar") }}</li>
                        <li>{{ __('Click on "Copy ID" then paste it it in the box below') }}</li>
                    </p>
                </div>
            </div>
            <div class="flex flex-row space-x-2 w-1/3">
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

            const response = await this.$axios.put("/api/settings", formData).catch(() => {
                this.$toast.error(this.__("Unable to save connection."));
            });

            if (!response?.data) return;

            this.$toast.info("Discord Server ID saved successfully");
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
