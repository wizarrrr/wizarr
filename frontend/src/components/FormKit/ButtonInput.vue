<template>
    <div class="flex flex-row">
        <div class="relative w-full">
            <div v-html="context._rawPrefixIcon" class="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none"></div>
            <input v-bind="attrs" :value="context._value" @keydown="listenEnter" @blur="context.handlers.blur" @touch="context.handlers.touch" @input="context.handlers.DOMInput" :class="inputClasses" class="h-[42px] w-full" />
        </div>
        <FormKit type="button" :disabled="buttonDisabled" @click="handleButton" :class="context.classes.button" :classes="buttonClasses">
            <component :is="context.slots.default" />
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "ButtonInput",
    props: {
        context: {
            type: Object as () => Record<string, any> & {
                classes: Record<string, any> & {
                    input: string;
                };
            },
            required: true,
        },
    },
    computed: {
        attrs() {
            return {
                id: this.context.id,
                type: "text",
                ...this.context.attrs,
            };
        },
        inputClasses() {
            return {
                ...this.context.classes.input.split(" ").reduce((acc: Record<string, boolean>, cur: string) => {
                    acc[cur] = true;
                    return acc;
                }, {}),
                "pl-10": this.context.prefixIcon,
            };
        },
        buttonClasses() {
            return {
                ...this.context.classes.button.split(" ").reduce((acc: Record<string, boolean>, cur: string) => {
                    acc[cur] = true;
                    return acc;
                }, {}),
                input: "!rounded-[0px] !rounded-r absolute inset-y-0 right-0 flex items-center px-2 h-[42px]",
            };
        },
    },
    data() {
        return {
            buttonDisabled: false,
        };
    },
    methods: {
        listenEnter(e: KeyboardEvent) {
            if (e.key === "Enter") {
                this.context.attrs.onButton();
            }
        },
        async handleButton() {
            this.buttonDisabled = true;
            await this.context.attrs.onButton();
            this.buttonDisabled = false;
        },
    },
});
</script>
