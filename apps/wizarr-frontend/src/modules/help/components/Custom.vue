<template>
    <MdPreview v-model="value" :theme="currentTheme" :language="currentLanguage" :sanitize="sanitize" />
</template>

<script lang="ts">
import { defineComponent, computed, toRefs, type PropType } from "vue";
import { MdPreview } from "md-editor-v3";
import { useThemeStore } from "@/stores/theme";
import { useLanguageStore } from "@/stores/language";

import type { Themes } from "md-editor-v3/lib/types";

export default defineComponent({
    name: "Custom",
    components: {
        MdPreview,
    },
    props: {
        value: {
            type: String,
            required: true,
        },
        sanitize: {
            type: Function as PropType<(html: string) => string>,
            default: (html: string) => html,
        },
    },
    setup(props) {
        const { value, sanitize } = toRefs(props);
        const themeStore = useThemeStore();
        const currentTheme = computed(() => themeStore.currentTheme);

        const languageStore = useLanguageStore();
        const currentLanguage = computed(() => languageStore.language);

        return {
            value,
            sanitize,
            currentTheme: currentTheme as unknown as Themes,
            currentLanguage,
        };
    },
});
</script>
