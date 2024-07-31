<template>
    <div ref="carousel" class="relative rounded overflow-hidden" style="transition: height 0.5s ease-in-out" :style="{ height: carouselHeight }">
        <template v-for="(view, index) in views" :key="index + 1">
            <div v-if="index == 0" :id="`carousel-item-${index}`"></div>
            <div :id="`carousel-item-${index + 1}`" class="hidden duration-700 ease-in-out">
                <section>
                    <div class="flex flex-col items-center justify-center">
                        <div class="relative w-full">
                            <div class="text-gray-900 dark:text-white" :class="classes.wrapper">
                                <template v-if="boxed">
                                    <div class="flex flex-col items-center justify-center md:container p-8 mx-auto">
                                        <div class="w-full md:w-1/2 lg:w-1/3 bg-white rounded shadow dark:border dark:bg-gray-800 dark:border-gray-700 overflow-hidden">
                                            <div class="relative">
                                                <div class="text-gray-900 dark:text-white">
                                                    <div class="block w-full" :class="classes.inner">
                                                        <component v-bind="_props[view.name] || view.props" @next="_carousel?.next()" @prev="_carousel?.prev()" @height="updateHeight()" :is="view.view" />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </template>
                                <template v-else>
                                    <component v-bind="_props[view.name] || view.props" @next="_carousel?.next()" @prev="_carousel?.prev()" @height="updateHeight()" :is="view.view" />
                                </template>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </template>
    </div>
</template>

<script lang="ts">
import { Carousel } from "flowbite";
import { defineComponent, markRaw } from "vue";
import { useEventListener } from "@vueuse/core";

import type { Component } from "vue";
import type { CarouselInterface, CarouselItem } from "flowbite";

import DefaultButton from "@/components/Buttons/DefaultButton.vue";
import DefaultLoading from "@/components/Loading/DefaultLoading.vue";

export interface CarouselViewProps {
    views: Array<{
        name: string;
        url?: string;
        view: Component;
        props?: Record<string, any>;
        disabled?: boolean;
    }>;
    currentView: number;
    callbacks: {
        onChange?: (carousel: CarouselInterface) => void;
        onNext?: (carousel: CarouselInterface) => void;
    };
    props: Record<string, any>;
    classes: Partial<{ wrapper: string; inner: string }>;
    boxed: boolean;
}

export default defineComponent({
    name: "Carousel",
    components: {
        DefaultButton,
        DefaultLoading,
    },
    props: {
        boxed: {
            type: Boolean as () => CarouselViewProps["boxed"],
            default: false,
            required: false,
        },
        classes: {
            type: Object as () => CarouselViewProps["classes"],
            default: () => ({
                wrapper: "px-6 pb-6 sm:px-8 sm:pb-8",
                inner: "",
            }),
            required: false,
        },
        views: {
            type: Array as () => CarouselViewProps["views"],
            required: true,
        },
        currentView: {
            type: Number as () => CarouselViewProps["currentView"],
            default: 1,
            required: false,
        },
        callbacks: {
            type: Object as () => CarouselViewProps["callbacks"],
            default: () => ({}),
            required: false,
        },
        props: {
            type: Object as () => CarouselViewProps["props"],
            default: () => ({}),
            required: false,
        },
    },
    data() {
        return {
            _carousel: null as Carousel | null,
            _views: this.views.map((view) => markRaw(view)),
            _currentView: this.currentView,
            _transitioning: false,
            _callbacks: this.callbacks,
            _props: this.props as Partial<Record<(typeof this.views)[number]["name"], Record<string, any>>>,
        };
    },
    methods: {
        getCarouselHeight(): string {
            const activeItem = this._carousel?._activeItem?.el;
            if (!activeItem) return "0px";

            const activeItemChild = activeItem.firstChild?.firstChild as HTMLElement | null;
            if (!activeItemChild) return "0px";

            return `${activeItemChild.offsetHeight}px`;
        },
        updateHeight() {
            setTimeout(() => {
                this.handleWindowResize();
            });
        },
        handleWindowResize() {
            const carouselRef = this.$refs.carousel as HTMLElement | null;
            if (!carouselRef) return;

            const carouselTransition = carouselRef.style.transition;
            carouselRef.style.transition = "none";
            carouselRef.style.height = this.getCarouselHeight();
            setTimeout(() => (carouselRef.style.transition = carouselTransition), 500);
        },
        onChange(carousel: CarouselInterface) {
            // Update current view index
            this._currentView = carousel._activeItem.position ?? 1;

            // Scroll to top of the page
            window.scrollTo({ top: 0, behavior: "smooth" });

            // Update URL to match current view
            const currentView = this._views[this._currentView - 1];
            if (currentView.url) this.$router.push(currentView.url);

            // Call the onChange callback
            this._callbacks?.onChange?.(carousel);
        },
    },
    computed: {
        carouselHeight(): string {
            return this.getCarouselHeight();
        },
    },
    watch: {
        currentView: {
            immediate: true,
            handler() {
                this._carousel?.slideTo(this.currentView);
            },
        },
        _currentView: {
            immediate: true,
            handler() {
                this.$emit("current", this._currentView);
            },
        },
    },
    async mounted() {
        // Get carousel items and map them to an array of objects
        const carouselViews = (this.$refs.carousel as HTMLElement).querySelectorAll('div[id^="carousel-item"]');
        const carouselItems = Array.from(carouselViews).map((view, index) => ({
            el: view,
            position: index,
        })) as CarouselItem[];

        // // Initialize carousel with items and options
        this._carousel = new Carousel(carouselItems, {
            defaultPosition: this._currentView,
            onChange: this.onChange,
            onNext: this._callbacks?.onNext ?? (() => {}),
        });

        (window as any)._carousel = this._carousel;

        // // Add event listeners for window resize
        useEventListener(window, "resize", this.handleWindowResize);
        useEventListener(this.$refs._carousel as HTMLElement, "transitionend", () => setTimeout(() => (this._transitioning = false), 500));
        useEventListener(this.$refs._carousel as HTMLElement, "transitionstart", () => (this._transitioning = true));
    },
    beforeUnmount() {
        // Remove event listeners for window resize
        window.removeEventListener("resize", this.handleWindowResize);
    },
});
</script>
