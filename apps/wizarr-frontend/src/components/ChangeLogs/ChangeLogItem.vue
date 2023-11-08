<template>
    <div class="flex w-full flex-col space-y-3 rounded bg-gray-800 p-3 shadow-md ring-1 ring-gray-700 sm:flex-row sm:space-y-0 sm:space-x-3">
        <div class="flex w-full flex-grow items-center justify-start space-x-4 truncate sm:justify-start">
            <div class="aspect-square h-full rounded flex items-center justify-center group-hover:bg-gray-200 dark:group-hover:bg-gray-600 transition duration-150 ease-in-out" :class="isCurrentVersion ? 'bg-green-400 dark:bg-green-500' : 'bg-gray-100 dark:bg-gray-700'">
                <i class="fa-solid fa-code-merge text-gray-400"></i>
            </div>
            <div class="dark:text-white flex flex-col items-start">
                <h2 class="text-sm font-bold truncate" :class="titleColor">
                    {{ changeLog.name }}
                </h2>
                <h4 class="text-xs font-semibold truncate text-gray-400">
                    {{ humanTimeAgo }}
                </h4>
            </div>
        </div>
        <DefaultButton class="flex-shrink-0" :href="changeLog.html_url" target="_blank" icon="fas fa-external-link" :options="{ icon: { icon_position: 'left' } }">
            {{ __("View") }}
        </DefaultButton>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import type { ChangeLog } from "@/types/ChangeLog";

import moment from "moment";
import DefaultButton from "../Buttons/DefaultButton.vue";

export default defineComponent({
    name: "ChangeLogItem",
    components: {
        DefaultButton,
    },
    props: {
        changeLog: {
            type: Object as () => ChangeLog,
            required: true,
        },
        version: {
            type: String,
            required: true,
        },
    },
    computed: {
        humanTimeAgo(): string {
            return moment(this.changeLog.created_at).fromNow();
        },
        titleColor() {
            if (this.changeLog.prerelease) {
                return "text-yellow-400";
            }
        },
        isCurrentVersion() {
            return this.changeLog.tag_name === this.version;
        },
    },
});
</script>
