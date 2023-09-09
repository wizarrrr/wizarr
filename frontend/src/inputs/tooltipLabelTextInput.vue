<template>
    <label :class="context.classes.label" :for="context.id">
        <span class="mr-1">{{ context.label }}</span>
        <span class="relative w-full" v-if="context.tooltip">
            <Popper arrow hover offsetDistance="23" placement="top" zIndex="20">
                <button type="button">
                    <i class="fa-solid fa-sm fa-info-circle text-gray-400 hover:text-gray-500"></i>
                </button>
                <template #content>
                    <div class="px-2 w-40">
                        <h3 v-if="context.tooltipTitle" class="font-semibold text-gray-900 dark:text-white">
                            {{ context.tooltipTitle }}
                        </h3>
                        <p class="text-xs">
                            {{ context.tooltip }}
                        </p>
                    </div>
                </template>
            </Popper>
        </span>
    </label>
    <!-- <input type="text" v-bind="attrs" :class="context.classes.input" :id="context.id" /> -->
</template>

<style lang="scss">
.formkit-outer[data-type="tooltipInput"] > .formkit-wrapper > label {
    display: none;
}
</style>

<script lang="ts">
import { defineComponent } from "vue";
import Popper from "vue3-popper";

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
        tooltip: string;
        tooltipTitle: string;
        attrs: {
            [key: string]: string;
        };
    };
}

// Create the component
export default defineComponent({
    components: {
        Popper,
    },
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
