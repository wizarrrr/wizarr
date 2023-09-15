<template>
    <div class="w-full h-full">
        <div class="flex flex-row-reverse justify-between p-3">
            <div class="flex items-center justify-end flex-grow">
                <div class="flex items-center justify-center">
                    <div class="bg-gray-100 rounded flex items-center justify-center dark:bg-gray-700 w-[60px] h-[60px]">
                        <i class="text-xl fa-solid text-gray-500 dark:text-gray-400" :class="icon"></i>
                    </div>
                </div>
            </div>
            <div class="text-left flex-grow text-xl leading-tight tracking-tight md:text-2xl">
                <div class="text-gray-400 dark:text-gray-300 mb-0 font-medium">{{ title }}</div>
                <div class="text-gray-300 dark:text-gray-200 text-xl font-bold">{{ value }}</div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "InvitesTotal",
    props: {
        icon: {
            type: String,
        },
        title: {
            type: String,
        },
        value: {
            type: String,
        },
    },
});
</script>
