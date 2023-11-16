<template>
    <FormKit type="button" v-bind="attrs" />
</template>

<script lang="ts">
import { defineComponent } from "vue";

type Theme = "primary" | "secondary" | "danger" | "success" | "warning" | "transparent" | "none";

export default defineComponent({
    name: "Button",
    props: {
        label: {
            type: String,
            default: "Button",
            required: false,
        },
        help: {
            type: String,
            default: "",
            required: false,
        },
        prefixIcon: {
            type: String,
            default: "",
            required: false,
        },
        suffixIcon: {
            type: String,
            default: "",
            required: false,
        },
        dataTheme: {
            type: String as () => Theme,
            default: "primary",
            required: false,
        },
        disabled: {
            type: Boolean,
            default: false,
            required: false,
        },
        onClick: {
            type: Function,
            default: () => {},
            required: false,
        },
    },
    computed: {
        attrs() {
            return {
                label: this.label,
                help: this.help,
                prefixIcon: this.prefixIcon,
                suffixIcon: this.suffixIcon,
                "data-theme": this.dataTheme,
                disabled: this.disabled,
                onClick: this.onClick,
            };
        },
    },
});
</script>
