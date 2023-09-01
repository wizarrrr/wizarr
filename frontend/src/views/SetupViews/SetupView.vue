<template>
    <div class="flex justify-center items-center flex-col mt-12 mb-3 space-y-2">
        <img style="width: 150px" src="@/assets/img/wizard.png" alt="logo" />
        <h1 class="text-3xl font-semibold text-center text-gray-900 dark:text-white">{{ __("Setup Wizarr") }}</h1>
    </div>

    <!-- Please Wait -->
    <div v-if="progress === null" class="flex justify-center items-center flex-col mt-12 mb-3 space-y-2">
        <DefaultLoading message="Please wait..." />
    </div>

    <!-- Setup Screens -->
    <div ref="carousel" class="relative overflow-hidden rounded h-screen" style="transition: max-height 0.5s ease-in-out" :style="{ maxHeight: carouselHeight }">
        <template v-for="(view, index) in views" :key="index + 1">
            <div v-if="index == 0" :id="`carousel-item-${index}`"></div>
            <div :id="`carousel-item-${index + 1}`" class="hidden duration-700 ease-in-out bg-gray-100 dark:bg-gray-900">
                <section>
                    <div class="flex flex-col items-center justify-center w-full md:w-2/3 lg:w-6/12 xl:w-5/12 2xl:w-3/12 py-8 md:mx-auto md:container px-2 sm:px-4 md:px-0">
                        <div class="relative w-full bg-transparent md:bg-gray-50 md:dark:bg-gray-800 rounded shadow md:dark:border dark:border-gray-700">
                            <div class="p-6 space-y-4 md:space-y-6 sm:p-8 text-gray-900 dark:text-white">
                                <component @nextSlide="handleNextSlide" @update:height="handleWindowResize" :is="view.view" />
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </template>
    </div>

    <!-- Back and Next Buttons -->
    <div class="flex justify-center mb-6 space-x-2" :class="{ hidden: progress === null || disableNav }">
        <DefaultButton @click="carousel?.prev()" :disabled="navDisabled.back" type="button" icon="fa-solid fa-arrow-left" :options="{ icon: { icon_position: 'left' } }">{{ __("Back") }}</DefaultButton>
        <DefaultButton @click="carousel?.next()" :disabled="navDisabled.next" type="button" icon="fa-solid fa-arrow-right" :options="{ icon: { icon_position: 'right' } }">{{ __("Next") }}</DefaultButton>
    </div>
</template>

<script lang="ts">
import { defineComponent, markRaw } from "vue";
import { Carousel, type CarouselInterface, type CarouselItem, type CarouselOptions } from "flowbite";
import { useEventListener } from "@vueuse/core";

import DefaultButton from "@/components/Buttons/DefaultButton.vue";
import DefaultLoading from "@/components/Loading/DefaultLoading.vue";
import DefaultToast from "@/components/Toasts/DefaultToast.vue";

import WelcomeView from "./WelcomeView.vue";
import DatabaseView from "./DatabaseView.vue";
import RestoreView from "./RestoreView.vue";
import AccountView from "./AccountView.vue";
import SettingsView from "./SettingsView.vue";
import CompleteView from "./CompleteView.vue";

export interface Progress {
    setup_required: boolean;
    setup_stage: SetupStage;
}

export interface SetupStage {
    accounts: boolean;
    settings: boolean;
}

export default defineComponent({
    name: "SetupView",
    components: {
        DefaultButton,
        DefaultLoading,
    },
    data() {
        return {
            carousel: null as Carousel | null,
            views: [
                {
                    name: "welcome",
                    view: markRaw(WelcomeView),
                    url: "/setup/welcome",
                },
                {
                    name: "database",
                    view: markRaw(DatabaseView),
                    url: "/setup/database",
                },
                {
                    name: "restore",
                    view: markRaw(RestoreView),
                    url: "/setup/restore",
                },
                {
                    name: "account",
                    view: markRaw(AccountView),
                    url: "/setup/account",
                },
                {
                    name: "settings",
                    view: markRaw(SettingsView),
                    url: "/setup/settings",
                },
                {
                    name: "complete",
                    view: markRaw(CompleteView),
                    url: "/setup/complete",
                },
            ],
            currentView: 1,
            progress: null as Progress | null,
            disabledSteps: ["account", "settings", "complete"],
            disableNav: false,
            transitioning: false,
            navDisabled: {
                back: false,
                next: false,
            },
        };
    },
    methods: {
        getCarouselHeight(): string {
            const activeItem = this.carousel?._activeItem?.el;
            if (!activeItem) return "0px";

            const activeItemChild = activeItem.firstChild as HTMLElement | null;
            if (!activeItemChild) return "0px";

            return `${activeItemChild.offsetHeight}px`;
        },
        handleWindowResize() {
            const carouselRef = this.$refs.carousel as HTMLElement | null;
            if (!carouselRef) return;

            const carouselTransition = carouselRef.style.transition;
            carouselRef.style.transition = "none";
            carouselRef.style.maxHeight = this.getCarouselHeight();
            setTimeout(() => (carouselRef.style.transition = carouselTransition), 500);
        },
        handleNextSlide(payload: { accounts?: boolean; settings?: boolean }) {
            if (payload.accounts) this.progress!.setup_stage.accounts = true;
            if (payload.settings) this.progress!.setup_stage.settings = true;
            this.carousel?.next();
        },
        onChange(carousel: CarouselInterface) {
            // Update current view index
            this.currentView = carousel._activeItem.position ?? 1;

            // Check if skip is required
            const skip = this.skipCompleted(this.currentView);

            // Skip to next step if required
            if (skip !== this.currentView) carousel.slideTo(skip);

            // Update URL to match current view
            const currentView = this.views[this.currentView - 1];
            this.$router.push(currentView.url);

            // Disable navigation buttons if first or last view
            if (this.currentView === 1) this.navDisabled.back = true;
            else this.navDisabled.back = false;

            if (this.currentView === this.views.length) this.navDisabled.next = true;
            else this.navDisabled.next = false;

            // Disable both buttons if current view is in disabled steps
            this.disableNav = this.disabledSteps.includes(currentView.name);
        },
        async onNext(carousel: CarouselInterface) {
            // Update current view index
            this.currentView = carousel._activeItem.position ?? 1;

            // Check if skip is required
            const skip = this.skipCompleted(this.currentView);

            // Skip to next step if required
            if (skip !== this.currentView) carousel.slideTo(skip);
        },
        getIndexFromUrl(url: string): number {
            return this.views.findIndex((view) => view.url.replace("/setup/", "") === url) - 1;
        },
        getIndexFromName(name: string): number {
            return this.views.findIndex((view) => view.name === name);
        },
        skipCompleted(attempt: number) {
            let stepIndex = attempt;

            // Skip account step if already completed
            if (stepIndex === this.getIndexFromName("settings") && this.progress?.setup_stage.accounts) {
                stepIndex++;
            }

            // Skip settings step if already completed
            if (stepIndex === this.getIndexFromName("settings") && this.progress?.setup_stage.settings) {
                stepIndex++;
            }

            // Go to account step if skipped to any step after it without completing it
            if (stepIndex - 1 > this.getIndexFromName("account") && !this.progress?.setup_stage.accounts) {
                stepIndex = this.getIndexFromName("account") + 1;
            }

            // Go to settings step if skipped to any step after it without completing it
            if (stepIndex - 1 > this.getIndexFromName("settings") && !this.progress?.setup_stage.settings) {
                stepIndex = this.getIndexFromName("settings") + 1;
            }

            return stepIndex;
        },
    },
    computed: {
        carouselHeight(): string {
            return this.getCarouselHeight();
        },
    },
    async mounted() {
        // Get progress from API
        const response = await this.$axios.get("/api/setup/status").catch((error) => {
            this.$toast.error(DefaultToast("Connection Error", "Failed to get setup progress"), { timeout: false, closeButton: false, draggable: false, closeOnClick: false });
            throw error;
        });

        // Set progress data
        this.progress = response.data;

        // Get carousel items and map them to an array of objects
        const carouselViews = (this.$refs.carousel as HTMLElement).querySelectorAll('div[id^="carousel-item"]');
        const carouselItems = Array.from(carouselViews).map((view, index) => ({
            el: view,
            position: index,
        })) as CarouselItem[];

        // Check if predefined position is requested
        const step = this.$route.params.step as string | undefined;
        let stepIndex = step ? this.getIndexFromUrl(step) + 2 : 1;

        // Skip completed steps
        stepIndex = this.skipCompleted(stepIndex);

        // Initialize carousel with items and options
        this.carousel = new Carousel(carouselItems, {
            defaultPosition: stepIndex,
            onChange: this.onChange,
            onNext: this.onNext,
        });

        // Add event listeners for window resize
        useEventListener(window, "resize", this.handleWindowResize);
        useEventListener(this.$refs.carousel as HTMLElement, "transitionend", () => setTimeout(() => (this.transitioning = false), 500));
        useEventListener(this.$refs.carousel as HTMLElement, "transitionstart", () => (this.transitioning = true));
    },
    beforeUnmount() {
        // Remove event listeners for window resize
        window.removeEventListener("resize", this.handleWindowResize);
    },
});
</script>
