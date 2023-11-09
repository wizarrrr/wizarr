<template>
    <label v-if="label" :for="name" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
        <span class="mr-1">{{ __(label) }}</span>
        <span v-if="sublabel" class="mr-1 text-gray-500">{{ __(sublabel) }}</span>
        <span class="relative w-full" v-else-if="tooltip">
            <Popper arrow hover offsetDistance="23" placement="top" zIndex="20">
                <button type="button">
                    <i class="fa-solid fa-sm fa-info-circle text-gray-400 hover:text-gray-500"></i>
                </button>
                <template #content>
                    <div class="px-2 w-40">
                        <h3 v-if="tooltipTitle" class="font-semibold text-gray-900 dark:text-white">
                            {{ __(tooltipTitle) }}
                        </h3>
                        <p class="text-xs">{{ __(tooltip) }}</p>
                    </div>
                </template>
            </Popper>
        </span>
        <!-- <span class="relative" v-else-if="tooltip">
            <button type="button" ref="tooltipBtn">
                <i class="fa-solid fa-sm fa-info-circle text-gray-400 hover:text-gray-500"></i>
            </button>
            <div ref="tooltipContent" class="invisible w-1/2 !mb-3 transition-opacity duration-300 absolute !top-15 left-0 p-2 text-sm font-light text-gray-500 bg-white border border-gray-200 rounded shadow-sm w-72 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-400">
                <div class="p-1.5" v-if="tooltipTitle">
                    <h3 v-if="tooltipTitle" class="font-semibold text-gray-900 dark:text-white">{{ __(tooltipTitle) }}</h3>
                    <p>{{ __(tooltip) }}</p>
                </div>
                <span v-else>{{ __(tooltip) }}</span>
            </div>
        </span> -->
    </label>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import Popper from "vue3-popper";

export default defineComponent({
    name: "DefaultLabel",
    components: {
        Popper,
    },
    props: {
        name: {
            type: String,
        },
        label: {
            type: String,
        },
        sublabel: {
            type: String,
        },
        tooltip: {
            type: String,
        },
        tooltipTitle: {
            type: String,
        },
    },
});
</script>
