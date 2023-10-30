<template>
    <div class="w-full h-full transition-opacity duration-300">
        <div class="flex flex-row-reverse justify-between p-3">
            <div class="flex items-center justify-end flex-grow">
                <div class="flex items-center justify-center">
                    <div class="bg-gray-100 rounded flex items-center justify-center dark:bg-gray-700 w-[60px] h-[60px] animate-pulse"></div>
                </div>
            </div>
            <div class="flex-grow space-y-2 w-full">
                <div class="rounded w-3/4 h-[2rem] animate-pulse bg-gray-100 dark:bg-gray-700 mb-0"></div>
                <div class="rounded w-1/2 h-[1.4rem] animate-pulse bg-gray-100 dark:bg-gray-700"></div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "LoadingWidget",
});
</script>
