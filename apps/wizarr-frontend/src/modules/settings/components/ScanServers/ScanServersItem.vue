<template>
    <button
        class="relative bg-white rounded shadow-md dark:bg-gray-800 dark:border dark:border-gray-700 overflow-hidden hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer group transition duration-150 ease-in-out"
    >
        <div class="flex flex-row justify-start p-3 items-center">
            <div
                class="aspect-square h-full p-3 bg-gray-100 rounded flex items-center justify-center dark:bg-gray-700 group-hover:bg-gray-200 dark:group-hover:bg-gray-600 transition duration-150 ease-in-out"
            >
                <component
                    :is="serverIcon"
                    width="800px"
                    height="800px"
                    class="w-6 h-6 fill-gray-500 dark:fill-gray-400 transition duration-150 ease-in-out"
                />
            </div>
            <div class="flex flex-col ml-4">
                <div
                    class="text-sm font-bold text-start leading-tight tracking-tight text-gray-900 md:text-md dark:text-gray-400 line-clamp-1"
                >
                    Plex Server
                </div>
                <div
                    class="text-xs text-start leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400 line-clamp-1"
                >
                    http://172.16.0.15:32400/
                </div>
            </div>
        </div>
    </button>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import DefaultIcon from '@/assets/img/logo/black/default.svg?component';
import JellyfinIcon from '@/assets/img/logo/black/jellyfin.svg?component';
import PlexIcon from '@/assets/img/logo/black/plex.svg?component';

export default defineComponent({
    name: 'ScanServersItem',
    props: {
        serverName: {
            type: String,
            required: false,
        },
        serverURL: {
            type: String,
            required: false,
        },
        serverType: {
            type: String,
            required: false,
        },
    },
    computed: {
        serverIcon() {
            switch (this.serverType) {
                case 'plex':
                    return PlexIcon;
                case 'jellyfin':
                    return JellyfinIcon;
                default:
                    return DefaultIcon;
            }
        },
    },
});
</script>
