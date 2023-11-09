<template>
    <div class="w-full h-full" :class="$slots.default ? '' : 'group-hover:opacity-50 transition-opacity duration-300'">
        <div v-if="icon !== undefined || title !== undefined || value !== undefined" class="flex flex-row-reverse justify-between" :class="$slots.default ? 'pb-3' : 'p-3'">
            <div class="flex items-center justify-end flex-grow">
                <div v-if="icon" class="flex items-center justify-center">
                    <div class="bg-gray-100 rounded flex items-center justify-center dark:bg-gray-700 w-[60px] h-[60px]">
                        <i class="text-xl fa-solid text-gray-500 dark:text-gray-400" :class="icon"></i>
                    </div>
                </div>
            </div>
            <div class="text-left flex-grow text-xl leading-tight tracking-tight md:text-2xl max-w-[calc(100%-70px)]">
                <div v-if="title" class="text-gray-500 dark:text-gray-300 mb-0 font-medium truncate text-ellipsis overflow-hidden">
                    {{ title }}
                </div>
                <div v-if="value" class="text-gray-400 dark:text-gray-200 text-xl font-bold truncate text-ellipsis overflow-hidden">
                    {{ value }}
                </div>
                <slot name="title"></slot>
                <slot name="value"></slot>
            </div>
        </div>
        <slot />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "InvitesTotal",
    props: {
        icon: {
            type: String,
            required: false,
        },
        title: {
            type: String,
            required: false,
        },
        value: {
            type: String,
            required: false,
        },
    },
});
</script>
