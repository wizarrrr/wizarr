<template>
    <!-- <template v-if="to">
        <router-link ref="button" :to="to" :class="btn_classes" class="flex items-center justify-center relative" :disabled="loading">
            <span class="absolute" :class="{ 'opacity-0': !loading }">
                <DefaultLoading icon_size="md"></DefaultLoading>
            </span>
            <span :class="{ 'opacity-0': loading }">
                <i v-if="icon && options.icon.icon_position === 'left'" :class="icon + ' ' + (options.icon?.icon_class ?? '') + ' mr-2'"></i>
                <slot></slot>
                <i v-if="icon && options.icon.icon_position === 'right'" :class="icon + ' ' + (options.icon?.icon_class ?? '') + ' ml-2'"></i>
            </span>
        </router-link>
    </template> -->
    <!-- <template> -->
    <button @click="handleClick" ref="button" :class="btn_classes + ' flex items-center justify-center relative'" :disabled="loading">
        <span class="absolute" :class="{ 'opacity-0': !loading }">
            <DefaultLoading icon_size="md"></DefaultLoading>
        </span>
        <span :class="{ 'opacity-0': loading }">
            <i v-if="icon && options.icon.icon_position === 'left'" :class="icon_classes"></i>
            <slot v-if="slotAvailable"></slot>
            <span v-else>{{ buttonText }}{{ label }}</span>
            <i v-if="icon && options.icon.icon_position === 'right'" :class="icon_classes"></i>
        </span>
    </button>
    <!-- </template> -->
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { RouterLink } from "vue-router";

import DefaultLoading from "@/components/Loading/DefaultLoading.vue";

export default defineComponent({
    name: "DefaultButton",
    components: {
        RouterLink,
        DefaultLoading,
    },
    props: {
        to: {
            type: String,
        },
        click: {
            type: Function,
            default: (payload: MouseEvent) => {},
        },
        icon: {
            type: String,
            default: "",
        },
        theme: {
            type: String as unknown as () => "primary" | "secondary" | "danger" | "transparent",
            default: "primary",
        },
        size: {
            type: String as unknown as () => "xs" | "sm" | "md" | "lg" | "xl",
            default: "md",
        },
        buttonText: {
            type: String,
            default: "",
        },
        label: {
            type: String,
            default: "",
        },
        options: {
            type: Object,
            default: () => ({
                icon: {
                    icon_position: "right",
                    icon_class: "",
                },
                text: {
                    text_class: "",
                },
                button: {
                    button_class: "",
                },
            }),
        },
        loading: {
            type: Boolean,
            default: false,
        },
        href: {
            type: String,
        },
        target: {
            type: String,
            default: "_self",
        },
    },
    computed: {
        btn_classes() {
            // Create classes array and add theme and size classes
            const classes = [this.themes[this.theme], this.sizes[this.size]];

            // Add button options classes
            if (this.options.button?.button_class) classes.push(this.options.button.button_class);

            // Add class to stop wrapping text
            classes.push("whitespace-nowrap overflow-hidden overflow-ellipsis");

            // Return classes as string
            return classes.join(" ");
        },
        icon_classes() {
            const classes = [this.icon, this.options.icon?.icon_class ?? ""];
            if (this.slotAvailable || this.buttonText || this.label) {
                if (this.options.icon.icon_position === "left") {
                    classes.push("mr-2");
                } else {
                    classes.push("ml-2");
                }
            }
            return classes.join(" ");
        },
        slotAvailable() {
            return this.$slots.default !== undefined;
        },
    },
    methods: {
        handleClick(payload: MouseEvent) {
            if (this.to) this.$router.push(this.to);
            else if (this.href) window.open(this.href, this.target);
            else this.click(payload);
        },
    },
    data() {
        return {
            themes: {
                primary: "bg-primary hover:bg-primary_hover focus:outline-none text-white font-medium rounded dark:bg-primary dark:hover:bg-primary_hover",
                secondary: "bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded dark:bg-secondary dark:hover:bg-secondary_hover",
                danger: "bg-red-600 hover:bg-red-500 focus:outline-none text-white font-medium rounded dark:bg-red-600 dark:hover:bg-primary_hover",
                transparent: "bg-none font-medium rounded text-gray-900 dark:text-white border border-gray-300 hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-700",
            },
            sizes: {
                xs: "px-3 py-2 text-xs",
                sm: "px-3 py-2 text-sm",
                md: "px-5 py-2.5 text-sm",
                lg: "px-6 py-3 text-base",
                xl: "px-8 py-4 text-lg",
            },
            isLoading: this.loading,
        };
    },
});
</script>
