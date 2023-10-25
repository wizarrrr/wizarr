<template>
    <div>
        <h5 class="mb-2 text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
            {{ __("Join & Download Plex for this device") }}
        </h5>
        <p class="mb-3 font-bold text-gray-700 dark:text-gray-400">
            {{ __("So you now have access to our server's media collection. Let's make sure you know how to use it with Plex.") }}
        </p>
        <p class="mb-3 font-normal text-gray-700 dark:text-gray-400">
            {{ __("Planning on watching Movies on this device? Download Plex for this device.") }}
        </p>

        <!-- Bottom Bar -->
        <div class="flex flex-row justify-between pt-4">
            <span class="flex justify-end items-end">
                <FormKit type="button" :classes="{ input: 'px-3 !py-2' }" @click="openURL">
                    {{ __("Open Plex") }}
                    <i class="fas fa-external-link-alt ml-2"></i>
                </FormKit>
            </span>
            <span class="flex justify-end items-center">
                <a href="https://www.plex.tv/en-gb/media-server-downloads/#plex-app" target="_blank" class="text-sm font-medium text-primary flex flex-row">
                    Other Download
                    <i class="fas fa-download ml-2 mt-[2px]"></i>
                </a>
            </span>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "Download",
    methods: {
        openURL() {
            const resolve = this.$router.resolve({ name: "open" });
            window.open(resolve.href, "_blank");
        },
    },
});
</script>
