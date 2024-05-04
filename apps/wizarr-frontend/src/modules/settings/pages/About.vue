<template>
    <div class="space-y-6 md:space-y-3">
        <div class="rounded border border-red-500 bg-red-400 bg-opacity-20 py-3 px-4 backdrop-blur" v-if="is_beta">
            <div class="flex">
                <div class="flex-shrink-0 justify-center items-center flex">
                    <i class="fa-solid fa-lg fa-circle-info text-gray-800 dark:text-gray-100"></i>
                </div>
                <div class="ml-3 flex-1 md:flex md:justify-between items-center">
                    <p class="text-sm leading-5 text-gray-800 dark:text-gray-100">This is BETA software. Features may be broken and/or unstable. Please report any issues on GitHub!</p>
                    <p class="mt-3 text-sm leading-5 md:mt-0 md:ml-6">
                        <a :href="`http://github.com/${GITHUB_SHEBANG}`" class="whitespace-nowrap font-medium text-gray-800 dark:text-gray-100 transition duration-150 ease-in-out hover:dark:text-white" target="_blank" rel="noreferrer">GitHub →</a>
                    </p>
                </div>
            </div>
        </div>

        <!-- Version Message Box -->
        <div class="rounded border border-gray-600 bg-gray-700 bg-opacity-20 py-3 px-4 backdrop-blur">
            <div class="flex flex-col md:flex-row md:justify-between items-center">
                <span class="">{{ __("Current Version") }}:</span>
                <span class="font-semibold">{{ version }}</span>
            </div>
        </div>

        <div class="max-h-[80vh] md:max-h-[50vh] overflow-y-scroll scrollbar-hide m-[-10px] p-[12px]">
            <ChangeLogs />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState } from "pinia";
import { useServerStore } from "@/stores/server";

import ChangeLogs from "@/components/ChangeLogs/ChangeLogs.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

export default defineComponent({
    name: "AboutView",
    components: {
        ChangeLogs,
        DefaultButton,
    },
    data() {
        return {
            APP_VERSION: "test",
            APP_RELEASED: false,
            APP_UPDATE: false,
            DATA_DIRECTORY: "test",
            TIMEZONE: "test",
            DOCS_URL: "test",
            GITHUB_SHEBANG: "wizarrrr/wizarr",
            DISCORD_INVITE: "test",
        };
    },
    computed: {
        ...mapState(useServerStore, ["version"]),
        ...mapState(useServerStore, ["is_beta"]),
    },
});
</script>
