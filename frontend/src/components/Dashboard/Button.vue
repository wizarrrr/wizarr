<template>
    <button type="button" class="inline-flex items-center rounded border text-sm font-medium text-slate-200 shadow-sm focus:outline-none" :class="classes">
        <slot />
    </button>
</template>
<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "Button",
    props: {
        size: {
            type: String, // sm | md | lg
            default: "md",
        },
        variant: {
            type: String, // primary | error
            default: "primary",
        },
        outline: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            classes: {
                "px-6 py-3": this.size === "lg",
                "px-4 py-2": this.size === "md",
                "px-2.5 py-1.5": this.size === "sm",
                "border-blue-500 bg-blue-500 hover:bg-blue-600 hover:border-blue-600": this.variant === "primary",
                "border-red-500 bg-red-500 text-red-500 hover:bg-red-600 hover:border-red-600": this.variant === "error",
                "bg-transparent hover:bg-transparent": this.outline,
            },
        };
    },
});
</script>
