<template>
    <MdEditor v-model="onboardingPage.value" :theme="currentTheme" .preview="false" language="en-US" />
</template>

<script lang="ts">
import { defineComponent, computed } from "vue";
import { MdEditor } from "md-editor-v3";
import { useThemeStore } from "@/stores/theme";
import Button from "@/components/Dashboard/Button.vue";

import type { Themes } from "md-editor-v3/lib/types";
import type { OnboardingPage } from "@/types/OnboardingPage";

export default defineComponent({
    name: "MarkdownEditor",
    components: {
        Button,
        MdEditor,
    },
    props: {
        onboardingPage: {
            type: Object as () => OnboardingPage,
            required: true,
        },
    },
    setup(props) {
        const themeStore = useThemeStore();
        const currentTheme = computed(() => themeStore.currentTheme);

        return {
            currentTheme: currentTheme as unknown as Themes,
            onboardingPage: props.onboardingPage,
        };
    },
});
</script>
