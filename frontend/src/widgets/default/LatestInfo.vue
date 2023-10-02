<template>
    <DefaultWidget icon="fa-info-circle">
        <template #title>
            <div class="text-[20px] mt-[-5px] text-gray-400 dark:text-gray-300 mb-0 font-medium truncate text-ellipsis overflow-hidden">{{ __("Latest Info") }}</div>
        </template>
        <template #value>
            <TextClamp :autoResize="true" :max-lines="2" :text="latestInfo" class="text-sm text-gray-400 dark:text-gray-300 mb-0">
                <template #after>
                    <button @click="readMore" class="ml-2 text-gray-500 hover:underline">{{ __("Read More") }}</button>
                </template>
            </TextClamp>
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
            latestInfo: this.$config("latest_info"),
        };
    },
    methods: {
        async readMore() {
            const latestInfoComponent = defineComponent({
                name: "LatestInfoModal",
                template: this.latestInfo,
            });

            this.$modal.openModal(latestInfoComponent, {
                title: this.__("Latest Info"),
                cancelButtonText: this.__("Close"),
            });
        },
    },
});
</script>
