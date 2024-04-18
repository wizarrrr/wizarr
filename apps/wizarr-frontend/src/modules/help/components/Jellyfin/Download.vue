<template>
    <div class="flex flex-col space-y-3 text-gray-700 dark:text-gray-400">
        <!-- Title -->
        <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
            {{ __("Join & Download") }}
        </h1>

        <!-- Subtitle -->
        <p class="font-semibold">
            {{ __("Great news! You now have access to our server's media collection. Let's make sure you know how to use it with Jellyfin.") }}
        </p>

        <!-- Split Line -->
        <hr class="border-gray-200 dark:border-gray-700" />

        <!-- Description -->
        <p class="text-sm">
            {{ __("Planning on watching Movies on this device? Download Jellyfin for this device or click 'Other Downloads' for other options.") }}
        </p>

        <!-- Split Line -->
        <hr class="border-gray-200 dark:border-gray-700" />

        <!-- Server URL -->
        <div class="flex flex-col justify-center items-center space-y-1 pt-3">
            <span class="font-semibold text-sm">{{ __("Server URL") }}</span>
            <div class="flex flex-row justify-center w-full">
                <input type="text" :value="settings.server_url_override ?? settings.server_url" class="text-center w-full p-2 bg-transparent border border-gray-200 rounded-l-lg rounded-r-none dark:border-gray-700 text-gray-700 dark:text-gray-400 px-5" readonly />
                <button @click="copy()" class="p-2 border border-gray-200 rounded-r-lg rounded-l-none dark:border-gray-700 dark:bg-gray-700 bg-primary text-gray-700 dark:text-gray-400 text-white px-5 cursor-pointer">
                    {{ __("Copy") }}
                </button>
            </div>
        </div>

        <!-- Bottom Bar -->
        <div class="flex flex-row justify-between pt-4">
            <span class="flex justify-end items-end">
                <template v-if="isIOS">
                    <DownloadAppStore to="itms-apps://apps.apple.com/ca/app/swiftfin/id1604098728" />
                </template>
                <template v-else-if="isAndroid">
                    <DownloadAndroid to="market://details?id=dev.jdtech.jellyfin" />
                </template>
                <template v-else-if="isLinux">
                    <DownloadLinux to="https://flathub.org/apps/com.github.iwalton3.jellyfin-media-player" />
                </template>
                <template v-else-if="isMac || isWindows">
                    <FormKit type="button" :classes="{ input: 'px-3 !py-2' }" @click="openURL">
                        {{ __("Open Jellyfin") }}
                        <i class="fas fa-external-link-alt ml-2"></i>
                    </FormKit>
                </template>
            </span>
            <span class="flex justify-end items-center">
                <a href="https://jellyfin.org/downloads" target="_blank" class="text-sm font-medium text-primary flex flex-row">
                    Other Downloads
                    <i class="fas fa-download ml-2 mt-[2px]"></i>
                </a>
            </span>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useServerStore } from "@/stores/server";
import { mapState } from "pinia";
import { useClipboard } from "@vueuse/core";

import browserDetect from "browser-detect";

import DownloadAppStore from "@/components/Buttons/DownloadButtons/DownloadAppStore.vue";
import DownloadAndroid from "@/components/Buttons/DownloadButtons/DownloadAndroid.vue";
import DownloadLinux from "@/components/Buttons/DownloadButtons/DownloadLinux.vue";

export default defineComponent({
    name: "DownloadView",
    components: {
        DownloadAppStore,
        DownloadAndroid,
        DownloadLinux,
    },
    data() {
        return {
            browser: browserDetect(),
            clipboard: useClipboard(),
        };
    },
    methods: {
        copy() {
            this.$toast.info("Copied to clipboard!");
            this.clipboard.copy(this.settings.server_url_override ?? this.settings.server_url);
        },
        openURL() {
            const resolve = this.$router.resolve({ name: "open" });
            window.open(resolve.href, "_blank");
        },
    },
    computed: {
        isIOS(): boolean {
            return (this.browser.os?.toLowerCase().includes("os x") && this.browser.mobile) ?? false;
        },
        isAndroid(): boolean {
            return (this.browser.os?.toLowerCase().includes("android") && this.browser.mobile) ?? false;
        },
        isMac(): boolean {
            return (this.browser.os?.toLowerCase().includes("os x") && !this.browser.mobile) ?? false;
        },
        isLinux(): boolean {
            return this.browser.os?.toLowerCase().includes("linux") ?? false;
        },
        isWindows(): boolean {
            return this.browser.os?.toLowerCase().includes("windows") ?? false;
        },
        ...mapState(useServerStore, ["settings"]),
    },
});
</script>
