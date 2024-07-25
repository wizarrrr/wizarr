<template>
    <MdPreview v-model="onboardingPage.value" :theme="currentTheme" language="en-US" />
</template>

<script lang="ts">
import { defineComponent, computed, toRefs } from "vue";
import { MdPreview } from "md-editor-v3";
import { useThemeStore } from "@/stores/theme";

import type { Themes } from "md-editor-v3/lib/types";
import type { OnboardingPage } from "../../../types/OnboardingPage";

export default defineComponent({
    name: "Custom",
    components: {
        MdPreview,
    },
    props: {
        onboardingPage: {
            type: Object as () => OnboardingPage,
            required: true,
        },
    },
    setup(props) {
        const { onboardingPage } = toRefs(props);
        const themeStore = useThemeStore();
        const currentTheme = computed(() => themeStore.currentTheme);

        return {
            onboardingPage,
            currentTheme: currentTheme as unknown as Themes,
        };
    },
});
</script>
