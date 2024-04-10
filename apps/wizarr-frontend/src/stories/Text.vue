<template>
    <FormKit type="text" v-bind="attrs" />
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "Input",
    props: {
        label: {
            type: String,
            default: "Label",
            required: false,
        },
        placeholder: {
            type: String,
            default: "Placeholder",
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
        disabled: {
            type: Boolean,
            default: false,
            required: false,
        },
    },
    computed: {
        attrs() {
            return {
                label: this.label,
                placeholder: this.placeholder,
                help: this.help,
                prefixIcon: this.prefixIcon,
                suffixIcon: this.suffixIcon,
                theme: this.theme,
                disabled: this.disabled,
            };
        },
    },
});
</script>
