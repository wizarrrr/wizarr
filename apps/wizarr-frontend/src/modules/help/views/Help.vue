<template>
    <div class="flex flex-row-reverse flex-column m-3">
        <LanguageSelector iconClasses="text-base h-6 w-6" />
        <ThemeToggle iconClasses="text-base h-6 w-6" />
    </div>

    <div>
        <div class="flex justify-center items-center flex-col mt-12 mb-3 space-y-6">
            <WizarrLogo rounded class="w-[150px] h-[150px]" />
            <h1 class="text-2xl font-semibold text-center text-gray-900 dark:text-white">
                {{ __("Getting Started!") }}
            </h1>
        </div>
        <section v-if="views.length">
            <Carousel :classes="{ wrapper: 'pt-6 sm:pt-8', inner: 'p-8' }" boxed :views="views" :currentView="currentView" @current="(current) => (currentView = current)" />
            <div id="navBtns" class="flex justify-center mb-6 space-x-2">
                <FormKit type="button" @click="currentView--" v-if="currentView !== 1">
                    <i class="fas fa-arrow-left mr-2"></i>
                    <span>{{ __("Back") }}</span>
                </FormKit>
                <FormKit type="button" @click="currentView++" v-if="currentView !== views.length">
                    <span>{{ __("Next") }}</span>
                    <i class="fas fa-arrow-right ml-2"></i>
                </FormKit>
                <FormKit type="button" @click="$router.push('/')" v-else>
                    <span>{{ __("Finish") }}</span>
                    <i class="fas fa-check ml-2"></i>
                </FormKit>
            </div>
        </section>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useServerStore } from "@/stores/server";
import { useOnboardingStore, TemplateType } from "@/stores/onboarding";
import { mapState } from "pinia";

import Carousel from "@/components/Carousel.vue";
import WizarrLogo from "@/components/WizarrLogo.vue";

import LanguageSelector from "@/components/Buttons/LanguageSelector.vue";
import ThemeToggle from "@/components/Buttons/ThemeToggle.vue";

import Request from "../components/Request.vue";
import Discord from "../components/Discord.vue";
import Download from "../components/Download.vue";
import Custom from "../components/Custom.vue";

import type { CarouselViewProps } from "@/components/Carousel.vue";

export default defineComponent({
    name: "HelpView",
    components: {
        Carousel,
        WizarrLogo,
        LanguageSelector,
        ThemeToggle,
    },
    data() {
        return {
            currentView: 1,
            views: [] as CarouselViewProps["views"],
        };
    },
    computed: {
        ...mapState(useServerStore, ["settings", "requests"]),
    },
    methods: {
        sanitize(html: string) {
            const onboardingStore = useOnboardingStore();
            Object.keys(onboardingStore.onboardingVariables).forEach((variable) => {
                const value = onboardingStore.onboardingVariables as Record<string, string>;
                html = html.replace(new RegExp(`{{${variable}}}`, "g"), value[variable]);
                html = html.replace(new RegExp(`%7B%7B${variable}%7D%7D`, "g"), value[variable]);
            });
            return html;
        },
        async getViews() {
            const onboardingStore = useOnboardingStore();
            await onboardingStore.getOnboardingPages();
            const views: CarouselViewProps["views"] = [];

            views.push(
                ...onboardingStore.enabledOnboardingPages.map((onboardingPage) => {
                    if (onboardingPage.template === TemplateType.Discord) {
                        return {
                            name: "discord",
                            view: Discord,
                        };
                    }
                    if (onboardingPage.template === TemplateType.Request) {
                        return {
                            name: "request",
                            view: Request,
                            props: {
                                requestURL: this.requests,
                            },
                        };
                    }
                    if (onboardingPage.template === TemplateType.Download) {
                        return {
                            name: "download",
                            view: Download,
                            props: {
                                value: onboardingPage.value,
                                sanitize: this.sanitize,
                            },
                        };
                    }
                    return {
                        name: "custom",
                        view: Custom,
                        props: {
                            value: onboardingPage.value,
                            sanitize: this.sanitize,
                        },
                    };
                }),
            );
            return views;
        },
    },
    mounted() {
        this.getViews().then((views) => {
            this.views = views;
        });
    },
});
</script>
