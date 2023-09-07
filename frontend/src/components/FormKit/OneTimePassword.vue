<template>
    <input v-for="index in Number(context.digits)" maxlength="1" :class="context.classes.digit" :value="tmp[index - 1] || ''" @input="handleInput(index - 1, $event)" @focus="handleFocus" @paste="handlePaste" />
</template>

<style scoped>
.formkit-digit {
    appearance: none;
    padding: 0.5em;
    box-sizing: border-box;
    width: 2em;
    margin-right: 0.25em;
    text-align: center;
    border: var(--fk-border);
    border-radius: var(--fk-border-radius);
}
</style>

<script lang="ts">
import { defineComponent } from "vue";

// Define the props type
interface MyProps {
    context: {
        classes: {
            digit: string;
        };
        digits: number;
        value: string;
        node: {
            input: (value: string) => void;
        };
    };
}

// Create the component
export default defineComponent({
    props: {
        context: {
            type: Object as () => MyProps["context"],
            required: true,
        },
    },
    data() {
        return {
            tmp: "",
        };
    },
    methods: {
        /**
         * Handle input, advancing or retreating focus.
         */
        handleInput(index: number, e: Event) {
            const prev = this.tmp;

            if (this.tmp.length <= index) {
                // If this is a new digit
                this.tmp = `${this.tmp}${(e.target as HTMLInputElement).value}`;
            } else {
                // If this digit is in the middle somewhere, cut the string into two
                // pieces at the index, and insert our new digit in.
                this.tmp = `${this.tmp.substring(0, index)}${(e.target as HTMLInputElement).value}${this.tmp.substring(index + 1)}`;
            }

            // Get all the digit inputs
            const inputs = (e.target as HTMLElement).parentElement?.querySelectorAll("input");

            if (index < this.context.digits - 1 && this.tmp.length >= prev.length) {
                // If this is a new input and not at the end, focus the next input
                inputs?.[index + 1]?.focus();
            } else if (index > 0 && this.tmp.length < prev.length) {
                // in this case we deleted a value, focus backwards
                inputs?.[index - 1]?.focus();
            }

            if (this.tmp.length === this.context.digits) {
                // If our input is complete, commit the value.
                this.context.node.input(this.tmp);
            } else if (this.tmp.length < this.context.digits && this.context.value !== "") {
                // If our input is incomplete, it should have no value.
                this.context.node.input("");
            }
        },

        /**
         * On focus, select the text in our input.
         */
        handleFocus(e: Event) {
            (e.target as HTMLInputElement).select();
        },

        /**
         * Handle the paste event.
         */
        handlePaste(e: ClipboardEvent) {
            const paste = e.clipboardData!.getData("text");
            if (typeof paste === "string") {
                // If it is the right length, paste it.
                this.tmp = paste.substring(0, this.context.digits);
                const inputs = (e.target as HTMLElement).parentElement?.querySelectorAll("input");
                // Focus on the last character
                inputs?.[this.tmp.length - 1]?.focus();
            }
        },
    },
    mounted() {
        // Set the initial value
        // this.tmp = this.context.value;
        console.log("this.context", this.context);
    },
});
</script>
