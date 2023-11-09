<template>
    <div>
        <DefaultLabel :name="name" :label="label" :sublabel="sublabel" :tooltip="tooltip" :tooltipTitle="tooltipTitle" />
        <div class="relative mb-6">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none" v-if="icon">
                <i :class="icon" class="text-gray-400"></i>
            </div>
            <input type="datetime-local" v-model="date" :disabled="disabled" :name="name" :required="required" :class="dateInputClass" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultLabel from "./DefaultLabel.vue";
import type { ToastID } from "vue-toastification/dist/types/types";

export default defineComponent({
    name: "DateTimeInput",
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
            type: String,
            default: "",
        },
        required: {
            type: Boolean,
            default: false,
        },
        disabled: {
            type: Boolean,
            default: false,
        },
        icon: {
            type: String,
            default: null as string | null,
        },
        inputClass: {
            type: String,
            default: "",
        },
        size: {
            type: String as () => "xs" | "sm" | "md" | "lg" | "xl",
            default: "md",
        },
        parsedOutput: {
            type: String as () => "default" | "days" | "hours" | "minutes" | "seconds",
            default: "default",
        },
        future: {
            type: Boolean,
            default: false,
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
            date: "",
            errorToast: null as ToastID | null,
        };
    },
    computed: {
        dateInputClass(): string {
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
    methods: {
        isFuture(date: string): boolean {
            return new Date(date).getTime() > Date.now();
        },
        parseDate(date: string): string | number {
            // If the output is default, return the date
            if (this.parsedOutput === "default") return date;

            // If the date is invalid, return the date
            if (isNaN(Date.parse(date))) return date;

            // If the date is valid, parse it
            const dateObject = new Date(date);

            // If the output is days, return the total days from now until the date
            if (this.parsedOutput === "days") return Number(Math.floor((dateObject.getTime() - Date.now()) / (1000 * 60 * 60 * 24)).toString());

            // If the output is hours, return the total hours from now until the date
            if (this.parsedOutput === "hours") return Number(Math.floor((dateObject.getTime() - Date.now()) / (1000 * 60 * 60)).toString());

            // If the output is minutes, return the total minutes from now until the date
            if (this.parsedOutput === "minutes") return Number(Math.floor((dateObject.getTime() - Date.now()) / (1000 * 60)).toString());

            // If the output is seconds, return the total seconds from now until the date
            if (this.parsedOutput === "seconds") return Number(Math.floor((dateObject.getTime() - Date.now()) / 1000).toString());

            return date;
        },
    },
    watch: {
        date: {
            handler(newValue: string) {
                // If future is true, check if the date is in the future if not clear the date
                if (this.future && !this.isFuture(newValue)) {
                    this.$toast.dismiss(this.errorToast as ToastID);
                    this.errorToast = this.$toast.error("The date must be in the future");
                    this.date = "";
                    return;
                }

                this.$emit("update:value", this.parseDate(newValue));
            },
        },
    },
    mounted() {
        // If the value is a valid date, set the date to the value
        if (this.value && !isNaN(Date.parse(this.value))) {
            this.date = this.value;
        }
    },
});
</script>
