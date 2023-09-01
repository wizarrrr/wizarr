<template>
    <span class="flex flex-col justify-center items-center space-y-2">
        <i class="fa-solid fa-spinner fa-spin dark:text-white" :class="classes"></i>
        <span v-if="message" class="text-gray-900 dark:text-white text-lg">{{ message }}</span>
    </span>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "DefaultLoading",
    props: {
        message: {
            type: String,
        },
        icon_size: {
            type: String as unknown as () => "xs" | "sm" | "md" | "lg" | "xl" | "2xl" | "3xl",
            default: "3xl",
        },
    },
    computed: {
        classes() {
            return {
                "text-xs": this.icon_size === "xs",
                "text-sm": this.icon_size === "sm",
                "text-base": this.icon_size === "md",
                "text-lg": this.icon_size === "lg",
                "text-xl": this.icon_size === "xl",
                "text-2xl": this.icon_size === "2xl",
                "text-3xl": this.icon_size === "3xl",
            };
        },
    },
});
</script>
