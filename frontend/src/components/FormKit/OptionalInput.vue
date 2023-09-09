<template>
    <label :class="context.classes.label" :for="context.id">
        <span class="mr-1">{{ context.label }}</span>
        <span class="mr-1 text-gray-500">(optional)</span>
    </label>
    <input type="text" v-bind="attrs" :class="context.classes.input" :id="context.id" />
</template>

<style lang="scss">
.formkit-outer[data-type="optionalInput"] > .formkit-wrapper > label {
    display: none;
}
</style>

<script lang="ts">
import { defineComponent } from "vue";

// Define the props type
interface MyProps {
    context: {
        id: string;
        classes: {
            input: string;
            label: string;
        };
        label: string;
        value: string;
        node: {
            input: (value: string) => void;
        };
        required: boolean;
        attrs: {
            [key: string]: string;
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
    computed: {
        attrs() {
            return Object.keys(this.context.attrs).reduce(
                (acc, key) => {
                    acc[key] = this.context.attrs[key];
                    return acc;
                },
                {} as { [key: string]: string },
            );
        },
    },
    mounted() {
        // Set the initial value
        // this.tmp = this.context.value;
        console.log("this.context", this.context);
    },
});
</script>
