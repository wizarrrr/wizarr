<template>
    <div class="flex flex-col justify-center items-start space-y-2">
        <span class="text-md font-semibold text-gray-900 dark:text-white">{{ title }}</span>
        <span class="text-sm text-gray-900 dark:text-white">{{ message }}</span>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "Error",
    props: {
        title: {
            type: String,
            required: true,
        },
        message: {
            type: String,
            required: true,
        },
    },
});
</script>
