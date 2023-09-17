<template>
    <div class="space-y-6 md:space-y-8">
        <div class="rounded border border-red-500 bg-red-400 bg-opacity-20 p-4 backdrop-blur">
            <div class="flex">
                <div class="flex-shrink-0">
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

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 md:px-2">
            <div>
                <h1 class="text-2xl font-bold dark:text-white">System Information</h1>
                <dl class="divide-y divide-gray-800 p-1 border-t border-gray-800 mt-4">
                    <div>
                        <div class="max-w-6xl py-4 sm:grid sm:grid-cols-3 sm:gap-4">
                            <dt class="block text-sm font-bold text-gray-600 dark:text-gray-400">Version</dt>
                            <dd class="flex text-sm dark:text-white sm:col-span-2 sm:mt-0">
                                <span class="flex-grow flex flex-row items-center truncate">
                                    <code class="truncate">{{ APP_VERSION }}</code>
                                    <template v-if="APP_RELEASED">
                                        <a :href="`https://github.com/${GITHUB_SHEBANG}`" target="_blank" rel="noopener noreferrer">
                                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full whitespace-nowrap cursor-default bg-yellow-500 bg-opacity-80 border border-yellow-500 !text-yellow-100 ml-2 !cursor-pointer transition hover:bg-yellow-400">Beta</span>
                                        </a>
                                    </template>
                                    <template v-else>
                                        <a :href="`https://github.com/${GITHUB_SHEBANG}/releases`" target="_blank" rel="noopener noreferrer">
                                            <template v-if="APP_UPDATE">
                                                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full whitespace-nowrap cursor-default bg-green-500 bg-opacity-80 border border-green-500 !text-green-100 ml-2 !cursor-pointer transition hover:bg-green-400">Up to Date</span>
                                            </template>
                                            <template v-else>
                                                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full whitespace-nowrap cursor-default bg-red-500 bg-opacity-80 border border-red-500 !text-red-100 ml-2 !cursor-pointer transition hover:bg-red-400">Update Available</span>
                                            </template>
                                        </a>
                                    </template>
                                </span>
                            </dd>
                        </div>
                    </div>
                    <div>
                        <div class="max-w-6xl py-4 sm:grid sm:grid-cols-3 sm:gap-4">
                            <dt class="block text-sm font-bold text-gray-600 dark:text-gray-400">Data Directory</dt>
                            <dd class="flex text-sm dark:text-white sm:col-span-2 sm:mt-0">
                                <span class="flex-grow undefined">
                                    <code>{{ DATA_DIRECTORY }}</code>
                                </span>
                            </dd>
                        </div>
                    </div>
                    <div>
                        <div class="max-w-6xl py-4 sm:grid sm:grid-cols-3 sm:gap-4">
                            <dt class="block text-sm font-bold text-gray-600 dark:text-gray-400">Time Zone</dt>
                            <dd class="flex text-sm dark:text-white sm:col-span-2 sm:mt-0">
                                <span class="flex-grow undefined">
                                    <code>{{ TIMEZONE }}</code>
                                </span>
                            </dd>
                        </div>
                    </div>
                </dl>
            </div>
            <div>
                <h1 class="text-2xl font-bold dark:text-white">Support</h1>
                <dl class="divide-y divide-gray-800 p-1 border-t border-gray-800 mt-4">
                    <div>
                        <div class="max-w-6xl py-4 sm:grid sm:grid-cols-3 sm:gap-4">
                            <dt class="block text-sm font-bold text-gray-600 dark:text-gray-400">Documentation</dt>
                            <dd class="flex text-sm dark:text-white sm:col-span-2 sm:mt-0">
                                <span class="flex-grow undefined">
                                    <a :href="`${DOCS_URL}`" target="_blank" rel="noreferrer" class="text-primary transition duration-300 hover:underline">{{ DOCS_URL }}</a>
                                </span>
                            </dd>
                        </div>
                    </div>
                    <div>
                        <div class="max-w-6xl py-4 sm:grid sm:grid-cols-3 sm:gap-4">
                            <dt class="block text-sm font-bold text-gray-600 dark:text-gray-400">GitHub Discussions</dt>
                            <dd class="flex text-sm dark:text-white sm:col-span-2 sm:mt-0">
                                <span class="flex-grow undefined">
                                    <a :href="`https://github.com/${GITHUB_SHEBANG}/discussions`" target="_blank" rel="noreferrer" class="text-primary transition duration-300 hover:underline">https://github.com/{{ GITHUB_SHEBANG }}/discussions</a>
                                </span>
                            </dd>
                        </div>
                    </div>
                    <div>
                        <div class="max-w-6xl py-4 sm:grid sm:grid-cols-3 sm:gap-4">
                            <div class="block text-sm font-bold text-gray-600 dark:text-gray-400">Discord</div>
                            <div class="flex text-sm dark:text-white sm:col-span-2 sm:mt-0">
                                <span class="flex-grow undefined">
                                    <a :href="`https://discord.gg/${DISCORD_INVITE}`" target="_blank" rel="noreferrer" class="text-primary transition duration-300 hover:underline">https://discord.gg/{{ DISCORD_INVITE }}</a>
                                </span>
                            </div>
                        </div>
                    </div>
                </dl>
            </div>
        </div>

        <ChangeLogs />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

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
            GITHUB_SHEBANG: "test",
            DISCORD_INVITE: "test",
        };
    },
});
</script>
