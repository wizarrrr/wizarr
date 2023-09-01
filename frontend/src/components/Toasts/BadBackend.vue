<template>
    <div class="flex flex-col justify-start items-start">
        <span class="text-md font-semibold text-gray-900 dark:text-white">Connection Error</span>
        <span class="text-sm text-gray-900 dark:text-white">We were unable to connect to the backend.</span>
        <span class="text-sm text-gray-900 dark:text-white">Wizarr may not function correctly.</span>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "BadBackend",
});
</script>
