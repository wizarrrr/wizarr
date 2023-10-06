<template>
    <div class="container flex flex-col items-center justify-center mx-auto text-secondary py-2 text-xs">
        {{ __("Wizarr") }}
    </div>
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
