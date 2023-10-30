<template>
    <DefaultWidget icon="fa-info-circle">
        <template #title>
            <div class="text-[20px] mt-[-5px] text-gray-500 dark:text-gray-300 mb-0 font-medium truncate text-ellipsis overflow-hidden">
                {{ __("Latest Info") }}
            </div>
        </template>
        <template #value>
            <template v-if="latestInfo">
                <TextClamp :autoResize="true" :max-lines="2" :text="latestInfo" class="text-sm text-gray-600 dark:text-gray-200 mb-0">
                    <template #after>
                        <button @click="readMore" class="ml-2 text-gray-500 hover:underline">
                            {{ __("Read More") }}
                        </button>
                    </template>
                </TextClamp>
            </template>
            <template v-else>
                <div class="flex flex-col space-y-1 mt-1">
                    <div class="rounded w-full h-[1rem] animate-pulse bg-gray-100 dark:bg-gray-700 mb-0"></div>
                    <div class="rounded w-3/4 h-[1rem] animate-pulse bg-gray-100 dark:bg-gray-700 mb-0"></div>
                </div>
            </template>
        </template>
    </DefaultWidget>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultWidget from "@/widgets/templates/DefaultWidget.vue";
import TextClamp from "vue3-text-clamp";

export default defineComponent({
    name: "LatestInfo",
    components: {
        DefaultWidget,
        TextClamp,
    },
    data() {
        return {
            latestInfo: null as string | null,
        };
    },
    computed: {
        newLineExplicit() {
            return this.$config("latest_info")?.replace(/(?:\r\n|\r|\n)/g, "<br />");
        },
    },
    methods: {
        async readMore() {
            this.$modal.openModal(this.newLineExplicit, {
                title: this.__("Latest Info"),
                cancelButtonText: this.__("Close"),
            });
        },
    },
    beforeMount() {
        this.latestInfo = this.$config("latest_info") ?? "Could not load latest info.";
    },
});
</script>
