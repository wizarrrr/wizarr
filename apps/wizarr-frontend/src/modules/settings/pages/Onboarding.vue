<template>
    <section class="flex flex-col items-center justify-center">
        <OnboardingSection disabled>
            <Welcome />
        </OnboardingSection>
        <OnboardingSection disabled>
            <Download />
        </OnboardingSection>
        <OnboardingSection v-if="settings.server_discord_id && settings.server_discord_id !== ''" disabled>
            <Discord />
        </OnboardingSection>
        <OnboardingSection v-if="requests && requests.length > 0" disabled>
            <Request .requestURL="requests" />
        </OnboardingSection>
        <OnboardingSection v-for="page in onboardingPages" .key="page.id" @clickMoveUp="movePageUp(page)" @clickMoveDown="movePageDown(page)" @clickEdit="editPage(page)" @clickDelete="deletePage(page)">
            <MdPreview :modelValue="page.value" :theme="currentTheme" language="en-US" />
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
import { useOnboardingStore } from "@/stores/onboarding";
import Welcome from "@/modules/help/components/Welcome.vue";
import Download from "@/modules/help/components/Download.vue";
import Discord from "@/modules/help/components/Discord.vue";
import Request from "@/modules/help/components/Request.vue";
import OnboardingSection from "../components/Onboarding/OnboardingSection.vue";
import EditOnboarding from "../components/Modals/EditOnboarding.vue";

import type { Themes } from "md-editor-v3/lib/types";
import type { OnboardingPage } from "@/types/OnboardingPage";

export default defineComponent({
    name: "Onboarding",
    components: {
        OnboardingSection,
        Welcome,
        Download,
        Discord,
        Request,
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
        const onboardingPages = computed(() => onboardingStore.enabledOnboardingPages);

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

        const editPage = (onboardingPage: OnboardingPage) => {
            const modal_options = {
                title: gettext.$gettext("Edit onboarding page"),
                disableCloseButton: true,
                buttons: [
                    {
                        text: gettext.$gettext("Save"),
                        onClick: () => {
                            console.log(onboardingPage);
                            onboardingStore.updateOnboardingPage({
                                id: onboardingPage.id,
                                value: onboardingPage.value,
                            });
                            modal.closeModal();
                        },
                    },
                ],
            };

            const modal_props = {
                onboardingPage: onboardingPage,
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

        return {
            currentTheme: currentTheme as unknown as Themes,
            settings,
            requests,
            onboardingPages,
            createPage,
            movePageUp,
            movePageDown,
            editPage,
            deletePage,
        };
    },
});
</script>
