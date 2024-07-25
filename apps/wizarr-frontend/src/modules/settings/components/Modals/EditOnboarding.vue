<template>
    <MdEditor v-model="onboardingPage.value" :theme="currentTheme" :preview="false" language="en-US" :toolbars="toolbars" :footers="['=', 'scrollSwitch']" />
</template>

<script lang="ts">
import { defineComponent, computed, ref } from "vue";
import { MdEditor } from "md-editor-v3";
import { useThemeStore } from "@/stores/theme";
import Button from "@/components/Dashboard/Button.vue";

import type { Themes, ToolbarNames } from "md-editor-v3";
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

        const toolbars = ref<ToolbarNames[]>(["bold", "underline", "italic", "-", "title", "strikeThrough", "sub", "sup", "quote", "-", "codeRow", "code", "link", "image", "table", "=", "preview", "pageFullscreen"]);

        return {
            currentTheme: currentTheme as unknown as Themes,
            onboardingPage: props.onboardingPage,
            toolbars,
        };
    },
});
</script>
