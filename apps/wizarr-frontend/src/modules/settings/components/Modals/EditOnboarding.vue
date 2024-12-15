<template>
    <MdEditor v-model="onboardingPage.value" :theme="currentTheme" :preview="false" :language="currentLanguage" :toolbars="toolbars" :footers="['=', 'scrollSwitch']" @onUploadImg="onUploadImg" :sanitize="sanitize">
        <template #defToolbars>
            <VariablesToolbar :variables="Object.keys(variables)" />
        </template>
    </MdEditor>
</template>

<script lang="ts">
import { defineComponent, computed, ref, type PropType } from "vue";
import { MdEditor, DropdownToolbar } from "md-editor-v3";
import Button from "@/components/Dashboard/Button.vue";
import { useThemeStore } from "@/stores/theme";
import { useLanguageStore } from "@/stores/language";
import { useAxios } from "@/plugins/axios";
import VariablesToolbar from "../MDToolbars/Variables.vue";

import type { Themes, ToolbarNames } from "md-editor-v3";
import type { OnboardingPage } from "@/types/api/onboarding/OnboardingPage";

export default defineComponent({
    name: "MarkdownEditor",
    components: {
        Button,
        MdEditor,
        DropdownToolbar,
        VariablesToolbar,
    },
    props: {
        onboardingPage: {
            type: Object as () => OnboardingPage,
            required: true,
        },
        variables: {
            type: Object as () => Record<string, string>,
            default: [],
        },
        sanitize: {
            type: Function as PropType<(html: string) => string>,
            default: (html: string) => html,
        },
    },
    setup(props) {
        const themeStore = useThemeStore();
        const currentTheme = computed(() => themeStore.currentTheme);

        const languageStore = useLanguageStore();
        const currentLanguage = computed(() => languageStore.language);

        const toolbars = ref<ToolbarNames[]>(["bold", "underline", "italic", "-", "title", "strikeThrough", "sub", "sup", "quote", "-", "codeRow", "code", "link", "image", "table", 0, "=", "preview", "pageFullscreen"]);

        const axios = useAxios();
        const onUploadImg = async (files: File[], callback: (files: string[]) => unknown) => {
            const res = await Promise.all(
                files.map((file) => {
                    const form = new FormData();
                    form.append("file", file);
                    return axios.post("/api/image", form, {
                        headers: {
                            "Content-Type": "multipart/form-data",
                        },
                    });
                }),
            );
            callback(
                res.map((item) => {
                    return `${window.location.protocol}//${window.location.host}/api/image/${item.data.filename}`;
                }),
            );
        };

        return {
            currentTheme: currentTheme as unknown as Themes,
            currentLanguage,
            onboardingPage: props.onboardingPage,
            toolbars,
            onUploadImg,
        };
    },
});
</script>
