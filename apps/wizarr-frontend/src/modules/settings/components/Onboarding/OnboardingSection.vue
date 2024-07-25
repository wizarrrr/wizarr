<template>
    <div class="w-full md:w-1/2 lg:w-1/3 m-3 bg-white rounded shadow dark:border dark:bg-gray-800 dark:border-gray-700 overflow-hidden">
        <div class="block w-full p-8">
            <slot></slot>
            <hr class="h-px my-8 bg-gray-200 border-0 dark:bg-gray-700" />
            <div class="flex flex-row">
                <button class="mr-1 inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-secondary border border-transparent rounded hover:bg-secondary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-secondsary-dark" .disabled="disabled || isFirst" @click="$emit('clickMoveUp')">
                    <i class="fas fa-arrow-up"></i>
                </button>
                <button class="mx-1 inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-secondary border border-transparent rounded hover:bg-secondary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-secondsary-dark" .disabled="disabled || isLast" @click="$emit('clickMoveDown')">
                    <i class="fas fa-arrow-down"></i>
                </button>
                <button class="mx-1 inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-secondary border border-transparent rounded hover:bg-secondary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-secondsary-dark" .disabled="disabled" @click="$emit('clickEdit')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="ml-1 inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-primary border border-transparent rounded hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-dark" .disabled="disabled" @click="$emit('clickDelete')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "OnboardingSection",
    emits: ["clickMoveUp", "clickMoveDown", "clickEdit", "clickDelete"],
    props: {
        disabled: {
            type: Boolean,
            default: false,
        },
        isFirst: {
            type: Boolean,
            default: false,
        },
        isLast: {
            type: Boolean,
            default: false,
        },
    },
    setup(props) {
        return {
            disabled: props.disabled,
            isFirst: props.isFirst,
            isLast: props.isLast,
        };
    },
});
</script>
