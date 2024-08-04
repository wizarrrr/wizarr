<template>
    <section class="flex flex-col items-center justify-center">
        <OnboardingSection v-for="page in onboardingPages" .key="page.id" :isEnabled="page.enabled" :disableDelete="!!page.template" :disableEdit="!page.editable" @clickMoveUp="movePageUp(page)" @clickMoveDown="movePageDown(page)" @clickEdit="editPage(page)" @clickDelete="deletePage(page)" @clickEnable="enablePage(page)">
            <div :class="{ 'opacity-50': !page.enabled }">
                <Discord v-if="page.template == TemplateType.Discord" />
                <Request v-else-if="page.template == TemplateType.Request" :requestURL="requests" />
                <Download v-else-if="page.template == TemplateType.Download" :value="page.value ?? ''" :sanitize="sanitize" />
                <MdPreview v-else :modelValue="page.value" :theme="currentTheme" :sanitize="sanitize" language="en-US" />
            </div>
        </OnboardingSection>
    </section>
    <div class="fixed right-6 bottom-6 group">
        <FormKit type="button" @click="createPage">
            <i class="fas fa-plus mr-2 transition-transform group-hover:rotate-45"></i>
            <span>{{ __("Add page") }}</span>
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent, computed, getCurrentInstance } from "vue";
import { MdPreview } from "md-editor-v3";
import { useGettext } from "vue3-gettext";
import { useServerStore } from "@/stores/server";
import { useThemeStore } from "@/stores/theme";
import { useOnboardingStore, TemplateType } from "@/stores/onboarding";
import Request from "@/modules/help/components/Request.vue";
import Discord from "@/modules/help/components/Discord.vue";
import Download from "@/modules/help/components/Download.vue";
import OnboardingSection from "../components/Onboarding/OnboardingSection.vue";
import EditOnboarding from "../components/Modals/EditOnboarding.vue";

import type { Themes } from "md-editor-v3";
import type { OnboardingPage } from "@/types/api/onboarding/OnboardingPage";

export default defineComponent({
    name: "Onboarding",
    components: {
        OnboardingSection,
        Request,
        Discord,
        Download,
        MdPreview,
    },
    setup() {
        const gettext = useGettext();

        const instance = getCurrentInstance();
        const modal = instance?.appContext.config.globalProperties.$modal!;
        const toast = instance?.appContext.config.globalProperties.$toast!;

        const themeStore = useThemeStore();
        const currentTheme = computed(() => themeStore.currentTheme);

        const serverStore = useServerStore();
        const settings = computed(() => serverStore.settings);
        const requests = computed(() => serverStore.requests);

        const onboardingStore = useOnboardingStore();
        onboardingStore.getOnboardingPages();
        const onboardingPages = computed(() => onboardingStore.onboardingPages);

        const onboardingVariables = computed(() => onboardingStore.onboardingVariables);

        const sanitize = (html: string) => {
            Object.keys(onboardingVariables.value).forEach((variable) => {
                const value = onboardingVariables.value as Record<string, string>;
                html = html.replace(new RegExp(`{{${variable}}}`, "g"), value[variable]);
                html = html.replace(new RegExp(`%7B%7B${variable}%7D%7D`, "g"), value[variable]);
            });
            return html;
        };

        const createPage = async () => {
            await onboardingStore.createOnboardingPage({
                value: gettext.$gettext("## **Onboarding page** using *markdown*\n\nEdit your newly created page by clicking the edit button."),
                enabled: true,
            });
            window.scrollTo(0, document.body.scrollHeight);
        };

        const movePageUp = async (onboardingPage: OnboardingPage) => {
            await onboardingStore.updateOnboardingPage({
                id: onboardingPage.id,
                order: onboardingPage.order - 1,
            });
        };

        const movePageDown = async (onboardingPage: OnboardingPage) => {
            await onboardingStore.updateOnboardingPage({
                id: onboardingPage.id,
                order: onboardingPage.order + 1,
            });
        };

        const editPage = (onboardingPage: OnboardingPage, fixed = false) => {
            const modal_options = {
                title: gettext.$gettext("Edit onboarding page"),
                disableCloseButton: true,
                buttons: [
                    {
                        text: gettext.$gettext("Save"),
                        onClick: () => {
                            onboardingStore.updateOnboardingPage(
                                {
                                    id: onboardingPage.id,
                                    value: onboardingPage.value,
                                },
                                fixed,
                            );
                            modal.closeModal();
                        },
                    },
                ],
            };

            const modal_props = {
                onboardingPage: onboardingPage,
                variables: onboardingVariables.value,
                sanitize,
            };
            modal.openModal(EditOnboarding, modal_options, modal_props);
        };

        const deletePage = async (onboardingPage: OnboardingPage) => {
            if (await modal.confirmModal(gettext.$gettext("Are you sure?"), gettext.$gettext("Are you sure you want to delete the onboarding page?"))) {
                onboardingStore.deleteOnboardingPage(onboardingPage.id);
            } else {
                toast.info(gettext.$gettext("Onboarding page deletion cancelled"));
            }
        };

        const enablePage = async (onboardingPage: OnboardingPage) => {
            await onboardingStore.updateOnboardingPage({
                id: onboardingPage.id,
                enabled: !onboardingPage.enabled,
            });
        };

        return {
            currentTheme: currentTheme as unknown as Themes,
            settings,
            requests,
            onboardingPages,
            sanitize,
            createPage,
            movePageUp,
            movePageDown,
            editPage,
            deletePage,
            enablePage,
            TemplateType,
        };
    },
});
</script>
