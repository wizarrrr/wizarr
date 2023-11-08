<template>
    <div>
        <DefaultLabel :name="name" :label="label" :sublabel="sublabel" :tooltip="tooltip" :tooltipTitle="tooltipTitle" />
        <div class="relative" :style="passwordMeter ? 'margin-bottom: -5px;' : ''">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none" v-if="icon">
                <i :class="icon" class="text-gray-400"></i>
            </div>
            <input ref="inputRef" @input="restrictValue" v-model="inputValue" :type="type" :name="name" :placeholder="__(placeholder)" :required="required" :autocomplete="autocomplete" :autofocus="autofocus" :class="inputClass" @keydown="restrictValue" :minlength="min" :maxlength="max" :pattern="pattern" :disabled="buttonLoading" />
            <PasswordMeter :password="inputValue" v-if="passwordMeter" />
            <DefaultButton
                @click="$emit('btnClick')"
                v-if="button"
                :loading="btnLoading"
                type="button"
                :theme="buttonTheme"
                :options="{
                    button: {
                        button_class: 'rounded-l-none !absolute !top-0 !right-0 !h-full ' + buttonClass,
                    },
                }">
                {{ __(button) }}
            </DefaultButton>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultButton from "../Buttons/DefaultButton.vue";
import DefaultLabel from "./DefaultLabel.vue";
import PasswordMeter from "vue-simple-password-meter";

export default defineComponent({
    name: "DefaultInput",
    components: {
        DefaultButton,
        DefaultLabel,
        PasswordMeter,
    },
    props: {
        label: {
            type: String,
        },
        sublabel: {
            type: String,
        },
        value: {
            type: String,
            default: "",
        },
        type: {
            type: String,
            default: "text",
        },
        name: {
            type: String,
            default: "",
        },
        placeholder: {
            type: String,
            default: "",
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
        size: {
            type: String as () => "xs" | "sm" | "md" | "lg" | "xl",
            default: "md",
        },
        min: {
            type: String as () => string | number,
        },
        max: {
            type: String as () => string | number,
        },
        pattern: {
            type: String,
        },
        uppercase: {
            type: Boolean,
            default: false,
        },
        restrictions: {
            type: Object,
            default: () => ({
                alpha: false,
                numeric: false,
                alpha_numeric: false,
                lowercase_only: false,
                uppercase_only: false,
                disable_spaces: false,
            }),
        },
        button: {
            type: String,
            default: null as string | null,
        },
        buttonTheme: {
            type: String as () => "primary" | "secondary" | "danger" | "transparent",
            default: "primary",
        },
        buttonClass: {
            type: String,
            default: "",
        },
        buttonLoading: {
            type: Boolean,
            default: false,
        },
        icon: {
            type: String,
        },
        tooltip: {
            type: String,
        },
        tooltipTitle: {
            type: String,
        },
        passwordMeter: {
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
            btnLoading: false,
            inputValue: this.value,
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
    methods: {
        restrictValue(event: Event) {
            const target = event.target as HTMLInputElement;

            if ((event as KeyboardEvent).key === "Enter") {
                this.$emit("enter", target.value);
                if (this.button) {
                    this.$emit("btnClick", target.value);
                }
            }

            if (this.min) {
                if (target.value.length < Number(this.min)) {
                    target.value = target.value.slice(0, Number(this.min));
                }
            }

            if (this.max) {
                if (target.value.length > Number(this.max)) {
                    target.value = target.value.slice(0, Number(this.max));
                }
            }

            if (this.restrictions.disable_spaces) {
                target.value = target.value.replace(/\s/g, "");
            }

            if (this.restrictions.alpha) {
                target.value = target.value.replace(/[^a-zA-Z]/g, "");
            }

            if (this.restrictions.numeric) {
                target.value = target.value.replace(/[^0-9]/g, "");
            }

            if (this.restrictions.alpha_numeric) {
                target.value = target.value.replace(/[^a-zA-Z0-9]/g, "");
            }

            if (this.restrictions.lowercase_only) {
                target.value = target.value.toLowerCase();
            }

            if (this.restrictions.uppercase_only) {
                target.value = target.value.toUpperCase();
            }
        },
        valueParse(value: string) {
            if (this.uppercase) {
                return value.toUpperCase();
            }

            return value;
        },
    },
    watch: {
        buttonLoading: {
            immediate: true,
            handler(newVal) {
                this.btnLoading = newVal;
            },
        },
        value: {
            immediate: true,
            handler(newVal) {
                this.inputValue = newVal;
            },
        },
        inputValue: {
            immediate: false,
            handler(newVal) {
                this.inputValue = this.valueParse(newVal);
                this.$emit("update:value", this.inputValue);
            },
        },
    },
    beforeMount() {
        this.btnLoading = this.buttonLoading;
        this.inputValue = this.valueParse(this.value);
    },
    mounted() {
        if (this.autofocus) {
            (this.$refs.inputRef as HTMLInputElement)?.focus();
        }
    },
});
</script>
