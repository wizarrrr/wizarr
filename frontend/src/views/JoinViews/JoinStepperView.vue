<template>
    <Stepper :steps="steps" v-model:active-step="activeStep" />
</template>

<script lang="ts">
import { defineComponent } from "vue";

import Stepper from "@/components/Stepper.vue";
import type { Emitter, EventType } from "mitt";

export default defineComponent({
    name: "JoinStepper",
    components: {
        Stepper,
    },
    props: {
        eventBus: {
            type: Object as () => Emitter<Record<EventType, unknown>>,
            required: false,
        },
    },
    data() {
        return {
            activeStep: 0,
            steps: [
                {
                    title: "Setting up your account",
                    icon: "fa-user-plus",
                },
                {
                    title: "Almost there!",
                    icon: "fa-user",
                },
                {
                    title: "All done!",
                    icon: "fa-check",
                },
            ],
        };
    },
    watch: {
        activeStep: {
            handler() {
                this.eventBus?.emit("activeStepTitle", this.steps[this.activeStep - 1] ? this.steps[this.activeStep - 1].title : "Please wait...");
            },
            immediate: true,
        },
    },
    mounted() {
        this.eventBus?.on("step", (step) => (this.activeStep = step as number));
    },
    unmounted() {
        this.eventBus?.off("step");
    },
});
</script>
