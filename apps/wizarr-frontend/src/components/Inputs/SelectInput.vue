<template>
    <div>
        <DefaultLabel :name="name" :label="label" :sublabel="sublabel" :tooltip="tooltip" :tooltipTitle="tooltipTitle" />
        <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none" v-if="icon">
                <i :class="icon" class="text-gray-400"></i>
            </div>
            <select ref="inputRef" v-model="selected" :disabled="disabled" :name="name" :placeholder="placeholder" :required="required" :autocomplete="autocomplete" :autofocus="autofocus" :class="inputClass">
                <option v-if="placeholder" value="disabled" disabled>
                    {{ placeholder }}
                </option>
                <slot></slot>
                <template v-for="option in options" :key="option.value">
                    <option :value="option.value" :selected="option.selected" :disabled="option.disabled">
                        {{ option.label }}
                    </option>
                </template>
            </select>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultLabel from "./DefaultLabel.vue";
import type { OptionHTMLAttributes } from "vue";

export default defineComponent({
    name: "SelectInput",
    components: {
        DefaultLabel,
    },
    props: {
        label: {
            type: String,
        },
        sublabel: {
            type: String,
        },
        tooltip: {
            type: String,
        },
        tooltipTitle: {
            type: String,
        },
        name: {
            type: String,
            default: "",
        },
        value: {
            type: String as () => string | number,
            default: "",
        },
        placeholder: {
            type: String,
            default: null as string | null,
        },
        required: {
            type: Boolean,
            default: false,
        },
        autocomplete: {
            type: String,
            default: "",
        },
        autofocus: {
            type: Boolean,
            default: false,
        },
        icon: {
            type: String,
            default: null as string | null,
        },
        size: {
            type: String as () => "xs" | "sm" | "md" | "lg" | "xl",
            default: "md",
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        options: {
            type: Object as () => OptionHTMLAttributes[],
        },
    },
    data() {
        return {
            classes: {
                background: "bg-gray-50 dark:bg-gray-700",
                font: "text-gray-900 dark:text-white sm:text-sm",
                border: "border border-gray-300 dark:border-gray-600",
                other: "rounded block w-full dark:placeholder-gray-400",
                focus: "focus:ring-primary focus:border-primary",
            },
            sizes: {
                xs: "p-1.5 text-xs",
                sm: "p-2 text-sm",
                md: "p-2.5 text-base",
                lg: "p-3 text-lg",
                xl: "p-4 text-xl",
            },
            selected: this.value,
        };
    },
    computed: {
        inputClass(): string {
            // Map all the classes to a string
            const classes = Object.keys(this.classes).map((key) => {
                return this.classes[key as keyof typeof this.classes];
            });

            // If icon add pl-10 to the classes
            if (this.icon) classes.push("pl-10");

            // Add the size class
            classes.push(this.sizes[this.size]);

            return classes.join(" ");
        },
    },
    watch: {
        selected: {
            handler(value: string) {
                this.$emit("update:value", value);
            },
            deep: true,
        },
        value: {
            handler(value: string) {
                this.selected = value;
            },
            deep: true,
        },
    },
    beforeMount() {
        if (this.placeholder) this.selected = "disabled";
    },
});
</script>
