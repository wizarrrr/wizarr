<template>
    <Stepper :steps="steps" v-model:active-step="activeStep" />
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import Stepper from '@/components/Stepper.vue';

export default defineComponent({
    name: 'JoinStepper',
    components: {
        Stepper,
    },
    props: {
        stepper: {
            type: Number,
            required: false,
        },
    },
    data() {
        return {
            activeStep: 0,
            steps: [
                {
                    title: 'Setting up your account',
                    icon: 'fa-user-plus',
                },
                {
                    title: 'Almost there!',
                    icon: 'fa-user',
                },
                {
                    title: 'All done!',
                    icon: 'fa-check',
                },
            ],
        };
    },
    watch: {
        activeStep: {
            handler() {
                const step = this.steps[this.activeStep - 1] as
                    | Record<string, string>
                    | undefined;
                if (step?.title) this.$emit('updateTitle', step.title);
            },
            immediate: true,
        },
        stepper: {
            handler(step) {
                this.activeStep = step;
            },
            immediate: true,
        },
    },
});
</script>
