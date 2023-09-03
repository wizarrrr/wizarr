<template>
    <div class="flex flex-row border dark:bg-gray-800 dark:border-gray-700 text-gray-900 p-4 rounded">
        <div class="flex flex-grow items-center justify-start space-x-0 md:space-x-3 w-2/3">
            <div class="aspect-square h-full bg-gray-100 rounded hidden md:flex items-center justify-center dark:bg-gray-700">
                <i :class="`fa-solid ${icon} text-gray-500 dark:text-gray-400`"></i>
            </div>
            <div class="dark:text-white font-bold flex flex-col items-start justify-between w-full">
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

export default defineComponent({
    name: "ListItem",
    props: {
        icon: {
            type: String,
            required: false,
            default: "fa-square",
        },
    },
});
</script>
