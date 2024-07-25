<template>
    <MdEditor v-model="onboardingPage.value" :theme="currentTheme" :preview="false" :language="currentLanguage" :toolbars="toolbars" :footers="['=', 'scrollSwitch']" />
</template>

<script lang="ts">
import { defineComponent, computed, ref } from "vue";
import { MdEditor } from "md-editor-v3";
import Button from "@/components/Dashboard/Button.vue";
import { useThemeStore } from "@/stores/theme";
import { useLanguageStore } from "@/stores/language";

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

        const languageStore = useLanguageStore();
        const currentLanguage = computed(() => languageStore.language);

        const toolbars = ref<ToolbarNames[]>(["bold", "underline", "italic", "-", "title", "strikeThrough", "sub", "sup", "quote", "-", "codeRow", "code", "link", "image", "table", "=", "preview", "pageFullscreen"]);

        return {
            currentTheme: currentTheme as unknown as Themes,
            currentLanguage,
            onboardingPage: props.onboardingPage,
            toolbars,
        };
    },
});
</script>
