<template>
    <div>
        <div class="flex justify-center items-center flex-col mt-12 mb-3 space-y-6">
            <WizarrLogo rounded class="w-[150px] h-[150px]" />
            <h1 class="text-2xl font-semibold text-center text-gray-900 dark:text-white">{{ __("Getting Started!") }}</h1>
        </div>
        <section>
            <Carousel :classes="{ wrapper: 'pt-6 sm:pt-8', inner: 'p-8' }" boxed :views="views" :currentView="currentView" @current="(current) => (currentView = current)" />
            <div id="navBtns" class="flex justify-center mb-6 space-x-2">
                <FormKit type="button" @click="currentView--" :disabled="currentView === 1">
                    <i class="fas fa-arrow-left mr-2"></i>
                    <span>{{ __("Back") }}</span>
                </FormKit>
                <FormKit type="button" @click="currentView++" :disabled="currentView === views.length">
                    <span>{{ __("Next") }}</span>
                    <i class="fas fa-arrow-right ml-2"></i>
                </FormKit>
            </div>
        </section>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import Carousel from "@/components/Carousel.vue";
import WizarrLogo from "@/components/WizarrLogo.vue";

import Welcome from "../components/Welcome.vue";
import Download from "../components/Download.vue";
// import Discord from "../components/Discord.vue";

export default defineComponent({
    name: "HelpView",
    components: {
        Carousel,
        WizarrLogo,
    },
    data() {
        return {
            currentView: 1,
            views: [
                {
                    name: "welcome",
                    view: Welcome,
                },
                {
                    name: "download",
                    view: Download,
                },
                // {
                //     name: "discord",
                //     view: Discord,
                // },
            ],
        };
    },
});
</script>
