<template>
    <div>
        <div v-if="carouselTitle" class="px-6 pt-6 sm:px-8 sm:pt-8">
            <h1
                class="relative text-lg md:text-xl font-bold leading-tight tracking-tight text-gray-900 dark:text-white"
            >
                <Transition
                    name="fade"
                    mode="out-in"
                    :duration="{ enter: 200, leave: 200 }"
                >
                    <div :key="carouselTitle">
                        {{ carouselTitle }}
                    </div>
                </Transition>
            </h1>
        </div>
        <div
            ref="carousel"
            class="relative overflow-hidden rounded h-screen"
            style="transition: max-height 0.5s ease-in-out"
            :style="{ maxHeight: carouselHeight }"
        >
            <template v-for="(view, index) in carouselViews" :key="index + 1">
                <div v-if="index == 0" :id="`carousel-item-${index}`"></div>
                <div
                    :id="`carousel-item-${index + 1}`"
                    class="hidden duration-700 ease-in-out"
                >
                    <div class="flex flex-col items-center justify-center">
                        <div class="relative w-full">
                            <div
                                class="text-gray-900 dark:text-white"
                                :class="
                                    hasTitle
                                        ? 'px-6 pb-6 pt-3 sm:px-8 sm:pb-8 sm:pt-4'
                                        : 'p-6 sm:p-8'
                                "
                            >
                                <Transition name="fade" mode="out-in">
                                    <template
                                        v-if="
                                            index + 1 == currentComponent &&
                                            view.asyncComponent
                                        "
                                    >
                                        <component
                                            v-bind="{ ...view.props, ...attrs }"
                                            :is="view.asyncComponent"
                                            :class="
                                                carouselWait ? 'hidden' : ''
                                            "
                                        />
                                    </template>
                                </Transition>
                            </div>
                        </div>
                    </div>
                </div>
            </template>
        </div>
        <Transition
            name="fade"
            mode="out-in"
            :duration="{ enter: 200, leave: 200 }"
        >
            <div
                class="z-20 bg-white dark:bg-gray-800 absolute top-0 right-0 bottom-0 left-0 flex justify-center items-center flex-col space-y-1"
                v-if="carouselWait"
            >
                <i
                    class="fa-solid fa-spinner fa-spin text-4xl text-center text-gray-900 dark:text-white"
                ></i>
                <p
                    class="text-center font-semibold text-gray-900 dark:text-white"
                >
                    {{ __('Please wait...') }}
                </p>
            </div>
        </Transition>
    </div>
</template>

<script lang="ts">
import { Carousel, type CarouselInterface, type CarouselItem } from 'flowbite';
import { defineAsyncComponent, defineComponent } from 'vue';
import { useResizeObserver, type UseResizeObserverReturn } from '@vueuse/core';

import type { Component } from 'vue';

export interface CarouselView {
    component: () => Promise<Component>;
    asyncComponent?: Component;
    props?: Record<string, any>;
    name?: string;
    title?: string;
}

export default defineComponent({
    name: 'Carousel',
    data() {
        return {
            carousel: null as CarouselInterface | null,
            carouselHeight: '100px',
            currentComponent: this.currentView,
            carouselViews: [] as CarouselView[],
            carouselWait: true,
            carouselTitle: this.pageTitle,
            stopObserver: null as UseResizeObserverReturn['stop'] | null,
        };
    },
    props: {
        views: {
            type: Array as () => CarouselView[],
            required: true,
        },
        currentView: {
            type: Number,
            default: 1,
            required: false,
        },
        pleaseWait: {
            type: Boolean,
            default: false,
            required: false,
        },
        pageTitle: {
            type: String as () => CarouselView['title'],
            default: undefined,
            required: false,
        },
    },
    methods: {
        getCarouselHeight(): string {
            const activeItem = this.carousel?._activeItem?.el;
            if (!activeItem) return '0px';

            const activeItemChild = activeItem.firstChild
                ?.firstChild as HTMLElement | null;
            if (!activeItemChild) return '0px';

            return `${activeItemChild.offsetHeight}px`;
        },
        updateHeight() {
            const carouselRef = this.$refs.carousel as HTMLElement | null;
            if (!carouselRef) return;

            const carouselTransition = carouselRef.style.transition;
            carouselRef.style.transition = 'none';
            carouselRef.style.maxHeight = this.getCarouselHeight();
            setTimeout(
                () => (carouselRef.style.transition = carouselTransition),
                500,
            );
        },
        awaitReference(ref: unknown): Promise<HTMLElement> {
            return new Promise((resolve) => {
                const interval = setInterval(() => {
                    if (ref) {
                        clearInterval(interval);
                        resolve(ref as HTMLElement);
                    }
                }, 100);
            });
        },
        carouselElements(carousel: HTMLElement): CarouselItem[] {
            const carouselElements = carousel.querySelectorAll(
                'div[id^="carousel-item"]',
            );
            return Array.from(carouselElements).map((element, index) => {
                return {
                    el: element,
                    position: index,
                } as CarouselItem;
            });
        },
        asyncComponent(component: CarouselView['component']) {
            return defineAsyncComponent({
                loader: component,
            });
        },
        mapViews() {
            return this.views.map((view) => {
                return {
                    ...view,
                    asyncComponent: this.asyncComponent(view.component),
                };
            });
        },
        handleCarouselChange(carousel: CarouselInterface) {
            // Stop resize observer if it's running
            if (this.stopObserver) this.stopObserver();

            // Update the carousel height to match the current view
            if (carousel?._activeItem?.el?.firstChild) {
                this.stopObserver = useResizeObserver(
                    carousel._activeItem.el.firstChild as HTMLElement,
                    (entry) => {
                        if (entry[0].target) {
                            if (this.carouselWait) return;
                            this.carouselHeight = `${
                                (entry[0].target as HTMLElement).offsetHeight
                            }px`;
                        }
                    },
                ).stop;
            }
        },
    },
    watch: {
        currentComponent: {
            handler(index: number) {
                // Update the carousel
                this.carousel?.slideTo(index);

                // Update the page title
                const view = this.carouselViews[index - 1];
                this.carouselTitle = view?.title ? view.title : undefined;
            },
            immediate: false,
        },
        currentView: {
            handler(index: number) {
                this.currentComponent = index;
            },
            immediate: false,
        },
        pleaseWait: {
            handler(value: boolean) {
                this.carouselWait = value;
            },
            immediate: false,
        },
    },
    computed: {
        hasTitle(): boolean {
            return !!this.carouselTitle;
        },
        attrs(): Record<string, any> {
            return {
                ...this.$attrs,
                onNextStep: () => this.currentComponent++,
                onPrevStep: () => this.currentComponent--,
                onPleaseWait: (value: boolean) => (this.carouselWait = value),
                onUpdateTitle: (title: string) => (this.carouselTitle = title),
                onHeight: () => this.updateHeight(),
            };
        },
    },
    async mounted() {
        // Map views to async components
        this.carouselViews = this.mapViews();

        // Wait for carousel to be mounted in DOM and then create an array of carousel elements
        const carouselRef = await this.awaitReference(this.$refs.carousel);
        const carouselElements = this.carouselElements(carouselRef);

        // Initialize carousel component with elements and options
        this.carousel = new Carousel(carouselElements, {
            defaultPosition: this.currentView,
            onChange: this.handleCarouselChange,
        });

        const view = this.carouselViews[this.currentView - 1];
        this.carouselTitle = view?.title ? view.title : undefined;

        this.carouselWait = this.pleaseWait ?? false;
    },
});
</script>
