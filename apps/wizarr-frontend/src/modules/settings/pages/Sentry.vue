<template>
    <div :class="bordered">
        <!-- Toggle Button for Bug Reporting -->
        <h2 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
            {{ __("Why We Use Bug Reporting") }}
        </h2>

        <p class="text-gray-500 dark:text-gray-100 mb-1">
            {{ __("We value the security and stability of our services. Bug reporting plays a crucial role in maintaining and improving our software.") }}
            {{ __("Here's why") }}:
        </p>

        <ul class="list-disc pl-8 mb-4">
            <li class="text-gray-500 dark:text-gray-100">{{ __("Error Monitoring") }}: {{ __("Bug reports helps us track and fix issues in real-time, ensuring a smoother user experience.") }}</li>
            <li class="text-gray-500 dark:text-gray-100">{{ __("Proactive Issue Resolution") }}: {{ __("It allows us to identify and resolve problems before they impact you.") }}</li>
            <li class="text-gray-500 dark:text-gray-100">{{ __("Performance Optimization") }}: {{ __("We can pinpoint bottlenecks and optimize our applications for better performance.") }}</li>
        </ul>

        <p class="text-gray-500 dark:text-gray-100 mb-4">
            {{ __("We want to clarify that our bug reporting system does not collect sensitive personal data. It primarily captures technical information related to errors and performance, such as error messages, stack traces, and browser information. Rest assured, your personal information is not at risk through this service being enabled.") }}
        </p>

        <FormKit type="toggle" name="toggle" off-value-label="Bug Reporting Off" on-value-label="Bug Reporting On" v-model="bugReporting" :classes="{ input: 'h-[36px]' }" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useThemeStore } from "@/stores/theme";
import { useServerStore } from "@/stores/server";
import { mapState } from "pinia";

export default defineComponent({
    name: "Sentry",
    data() {
        return {
            bugReporting: true,
        };
    },
    computed: {
        bordered() {
            return !this.boxView ? "border border-gray-200 dark:border-gray-700 rounded-md p-6" : "";
        },
        ...mapState(useServerStore, ["settings", "isBugReporting"]),
        ...mapState(useThemeStore, ["boxView"]),
    },
    watch: {
        bugReporting: {
            immediate: false,
            handler() {
                const formData = new FormData();
                formData.append("bug_reporting", this.bugReporting as unknown as string);

                this.$axios.put("/api/settings", formData).catch(() => {
                    this.$toast.error(this.__("Unable to save bug reporting settings."));
                });
            },
        },
    },
    beforeMount() {
        this.bugReporting = this.isBugReporting ?? true;
    },
});
</script>
