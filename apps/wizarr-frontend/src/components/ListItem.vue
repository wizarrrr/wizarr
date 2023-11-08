<template>
    <div class="flex flex-row border bg-white dark:bg-gray-800 dark:border-gray-700 text-gray-900 p-4 rounded overflow-hidden">
        <div class="flex flex-grow items-center justify-start space-x-0 md:space-x-3 w-2/3">
            <div v-if="icon" class="aspect-square h-full bg-gray-100 rounded hidden md:flex items-center justify-center dark:bg-gray-700">
                <i :class="`fa-solid ${icon} text-xl text-gray-500 dark:text-gray-400`"></i>
            </div>
            <div v-else-if="svgIcon" class="aspect-square h-full bg-gray-100 rounded hidden md:flex items-center justify-center dark:bg-gray-700">
                <component :is="svgIcon" class="p-2.5 w-[50px] opacity-70"></component>
            </div>
            <div v-else-if="svgString" class="aspect-square h-full bg-gray-100 rounded hidden md:flex items-center justify-center dark:bg-gray-700">
                <div v-html="svgString" class="p-2.5 w-[50px] opacity-70"></div>
            </div>
            <div v-else-if="iconSlotAvailable" class="aspect-square h-full hidden md:flex items-center justify-center">
                <slot name="icon"></slot>
            </div>
            <div class="dark:text-white font-bold flex flex-col items-start justify-between w-full overflow-hidden truncate">
                <slot name="title"></slot>
            </div>
        </div>

        <div class="flex flex-row space-x-3 justify-end items-center w-1/2">
            <slot name="buttons"></slot>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import type { Component } from "vue";

export default defineComponent({
    name: "ListItem",
    props: {
        icon: {
            type: String,
            required: false,
        },
        svgIcon: {
            type: Object as () => Component,
            required: false,
        },
        svgString: {
            type: String,
            required: false,
        },
    },
    computed: {
        iconSlotAvailable(): boolean {
            return !!this.$slots.icon;
        },
    },
});
</script>
