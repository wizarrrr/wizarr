<template>
    <!-- <nav class="bg-white dark:bg-gray-900 absolute w-full z-20 bottom-0 left-0 border-t border-gray-200 dark:border-gray-600 h-[33px] flex items-center justify-center">
        <div class="flex flex-row items-center justify-center text-gray-700 dark:text-gray-600">
            <span>Wizarr</span>
        </div>
    </nav> -->
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "DefaultFooter",
    data() {
        return {
            APP_NAME: "",
            APP_VERSION: "",
            APP_RELEASED: "",
            APP_GITHUB_URL: "",
        };
    },
});
</script>
