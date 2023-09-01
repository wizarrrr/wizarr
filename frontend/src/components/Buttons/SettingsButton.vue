<template>
    <router-link as="button" :to="disabled ? '' : url" class="relative bg-white rounded shadow-md dark:bg-gray-800 dark:border dark:border-gray-700 overflow-hidden hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer group transition duration-150 ease-in-out" :class="{ 'opacity-50 cursor-not-allowed': disabled, classes: classes }" :disabled="disabled">
        <div class="flex flex-row justify-start p-3 items-center">
            <div class="aspect-square h-full p-3 bg-gray-100 rounded flex items-center justify-center bg-gray-100 dark:bg-gray-700 group-hover:bg-gray-200 dark:group-hover:bg-gray-600 transition duration-150 ease-in-out">
                <i class="text-gray-400" :class="icon"></i>
            </div>
            <div class="flex flex-col ml-4">
                <div class="settings-item-title text-sm font-bold text-start leading-tight tracking-tight text-gray-900 md:text-md dark:text-gray-400 line-clamp-1">
                    {{ __(title) }}
                </div>
                <div class="settings-item-description text-xs text-start leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400 line-clamp-1">
                    {{ __(description) }}
                </div>
            </div>
        </div>
    </router-link>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "SettingsButton",
    props: {
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            required: true,
        },
        icon: {
            type: String,
            required: true,
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        classes: {
            type: String,
            default: "",
        },
        url: {
            type: String,
            default: "",
        },
    },
});
</script>
