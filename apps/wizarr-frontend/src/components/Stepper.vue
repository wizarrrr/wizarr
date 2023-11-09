<template>
    <ol id="stepper" class="flex items-center w-full">
        <template v-for="(step, index) in steps">
            <li class="flex items-center" :class="getStepClasses(index)" :style="stepStyles">
                <span class="flex items-center justify-center w-10 h-10 rounded-full lg:h-12 lg:w-12 shrink-0" :class="getStepSpanClasses(index)" style="transition: background-color 0.3s ease">
                    <i class="fas" :class="step.icon"></i>
                </span>
            </li>
        </template>
    </ol>
</template>

<script lang="ts">
import { defineComponent } from "vue";

interface Step {
    title: string;
    icon: string;
}

export default defineComponent({
    name: "Stepper",
    props: {
        steps: {
            type: Array as () => Step[],
            required: true,
        },
        activeStep: {
            type: Number,
            required: false,
        },
    },
    data() {
        return {
            _activeStep: this.activeStep ?? 0,
            stepClasses: "w-full after:content-[''] after:w-full after:h-1 after:border-b after:border-4 after:inline-block",
            stepStyles: "transition: border-color 0.3s ease",
            stepActive: "after:border-primary",
            stepInactive: "after:border-gray-100 after:dark:border-gray-700",
            stepSpanActive: "bg-primary",
            stepSpanInactive: "bg-gray-100 dark:bg-gray-700",
        };
    },
    methods: {
        getStepClasses(index: number): string {
            const border = index < this._activeStep ? this.stepActive : this.stepInactive;
            const defaults = index < this.steps.length - 1 ? this.stepClasses : "";
            return `${defaults} ${border}`;
        },
        getStepSpanClasses(index: number): string {
            return index < this._activeStep ? this.stepSpanActive : this.stepSpanInactive;
        },
    },
    watch: {
        _activeStep: {
            handler() {
                this.$emit("update:activeStep", this._activeStep);
            },
            immediate: true,
        },
        activeStep: {
            handler() {
                this._activeStep = this.activeStep ?? 0;
            },
            immediate: true,
        },
    },
});
</script>
