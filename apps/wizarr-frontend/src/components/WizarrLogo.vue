<template>
    <Logo :class="{ 'rounded-full': rounded, [svgSize]: true }" :viewBox="svgZoom" />
</template>

<script lang="ts">
import { defineComponent } from "vue";

import Logo from "@/assets/img/wizarr-logo.svg?component";

export default defineComponent({
    name: "WizarrLogo",
    components: {
        Logo,
    },
    props: {
        size: {
            type: String as () => "xxs" | "xs" | "md" | "lg" | "xl" | "2xl" | "3xl",
            default: "md",
        },
        rounded: {
            type: Boolean,
            default: false,
        },
        zoom: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        svgZoom() {
            const minX = 55;
            const minY = 50;
            const width = 500;
            const height = 500;

            return `${minX} ${minY} ${width} ${height}`;
        },
        svgSize() {
            switch (this.size) {
                case "xxs":
                    return "w-4 h-4";
                case "xs":
                    return "w-6 h-6";
                case "md":
                    return "w-8 h-8";
                case "lg":
                    return "w-12 h-12";
                case "xl":
                    return "w-16 h-16";
                case "2xl":
                    return "w-20 h-20";
                case "3xl":
                    return "w-24 h-24";
                default:
                    return "w-8 h-8";
            }
        },
    },
});
</script>
