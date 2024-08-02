<template>
    <div class="w-full md:w-1/2 lg:w-1/3 m-3 bg-white rounded shadow dark:border dark:bg-gray-800 dark:border-gray-700 overflow-hidden">
        <div class="block w-full p-8">
            <slot></slot>
            <hr class="h-px my-8 bg-gray-200 border-0 dark:bg-gray-700" />
            <div class="flex flex-row">
                <VTooltip v-for="button in buttons" .key="button.action">
                    <button class="mx-1 px-4 py-2 text-white bg-secondary border border-transparent rounded hover:bg-secondary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-secondsary-dark" .disabled="button.disabled" @click="$emit(button.action)">
                        <i class="fas" :class="button.icon"></i>
                    </button>

                    <template #popper>
                        <span>{{ button.label }}</span>
                    </template>
                </VTooltip>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

type events = "clickMoveUp" | "clickMoveDown" | "clickEdit" | "clickDelete";
interface button {
    icon: string;
    action: events;
    disabled: boolean;
    label: string;
}

export default defineComponent({
    name: "OnboardingSection",
    emits: ["clickMoveUp", "clickMoveDown", "clickEdit", "clickDelete"] as events[],
    props: {
        disabledReorder: {
            type: Boolean,
            default: false,
        },
        disableDelete: {
            type: Boolean,
            default: false,
        },
        disableEdit: {
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
    computed: {
        buttons() {
            return [
                {
                    icon: "fa-arrow-up",
                    action: "clickMoveUp",
                    disabled: this.disabledReorder || this.isFirst,
                    label: this.__("Move up"),
                },
                {
                    icon: "fa-arrow-down",
                    action: "clickMoveDown",
                    disabled: this.disabledReorder || this.isLast,
                    label: this.__("Move down"),
                },
                {
                    icon: "fa-edit",
                    action: "clickEdit",
                    disabled: this.disableEdit,
                    label: this.__("Edit"),
                },
                {
                    icon: "fa-trash",
                    action: "clickDelete",
                    disabled: this.disableDelete,
                    label: this.__("Delete"),
                },
            ] as button[];
        },
    },
});
</script>
