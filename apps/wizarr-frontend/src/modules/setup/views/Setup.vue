<template>
    <div class="flex flex-row-reverse flex-column m-3">
        <LanguageSelector iconClasses="text-base h-6 w-6" />
        <ThemeToggle iconClasses="text-base h-6 w-6" />
    </div>

    <div>
        <div
            class="flex justify-center items-center flex-col mt-12 mb-3 space-y-6"
        >
            <WizarrLogo rounded class="w-[150px] h-[150px]" />
            <h1
                class="text-3xl font-semibold text-center text-gray-900 dark:text-white"
            >
                {{ __('Setup Wizarr') }}
            </h1>
        </div>
        <section>
            <div
                class="flex flex-col items-center justify-center md:container py-8 mx-auto"
            >
                <div
                    class="w-full md:w-1/2 lg:w-1/3 bg-white rounded shadow dark:border dark:bg-gray-800 dark:border-gray-700 overflow-hidden"
                >
                    <div class="relative">
                        <Carousel
                            :views="views"
                            :currentView="currentView"
                            :pleaseWait="pleaseWait"
                        />
                    </div>
                </div>
            </div>
        </section>
        <Transition name="fade" mode="out-in">
            <div
                class="flex justify-center items-center flex-row space-x-3"
                v-if="!disabledNavigation"
            >
                <FormKit
                    type="button"
                    @click="currentView--"
                    prefix-icon="fa-solid fa-arrow-left"
                    :disabled="currentView === 1"
                >
                    {{ __('Back') }}
                </FormKit>
                <FormKit
                    type="button"
                    @click="currentView++"
                    suffix-icon="fa-solid fa-arrow-right"
                    :disabled="currentView === views.length"
                >
                    {{ __('Next') }}
                </FormKit>
            </div>
        </Transition>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import Carousel from '../../core/components/Carousel.vue';
import WizarrLogo from '@/components/WizarrLogo.vue';

import LanguageSelector from '@/components/Buttons/LanguageSelector.vue';
import ThemeToggle from '@/components/Buttons/ThemeToggle.vue';

export default defineComponent({
    name: 'Setup',
    components: {
        WizarrLogo,
        Carousel,
        LanguageSelector,
        ThemeToggle,
    },
    data() {
        return {
            pleaseWait: true,
            currentView: 1,
            views: [
                {
                    name: 'welcome',
                    component: () => import('../pages/Welcome.vue'),
                },
                {
                    name: 'database',
                    component: () => import('../pages/Database.vue'),
                },
                {
                    name: 'restore',
                    component: () => import('../pages/Restore.vue'),
                },
                {
                    name: 'account',
                    component: () => import('../pages/Account.vue'),
                },
                {
                    name: 'settings',
                    component: () => import('../pages/Settings.vue'),
                },
                {
                    name: 'complete',
                    component: () => import('../pages/Complete.vue'),
                },
            ],
        };
    },
    methods: {
        findIndex(names: string[]): number[] {
            const indexArray = [];

            for (const name of names) {
                indexArray.push(
                    this.views.findIndex((view) => view.name === name) + 1,
                );
            }

            return indexArray;
        },
    },
    computed: {
        disabledNavigation() {
            return this.findIndex(['account', 'settings', 'complete']).includes(
                this.currentView,
            );
        },
    },
    watch: {
        currentView: {
            immediate: true,
            handler() {
                console.log(this.currentView);
            },
        },
    },
    async mounted() {
        this.$nextTick(() => {
            this.$toast.info('Welcome to Wizarr!');
        });

        const response = await this.$axios
            .get('/api/setup/status')
            .catch(() => {
                this.$toast.error('Could not get setup status');
                this.pleaseWait = false;
            });

        if (!response?.data) return;

        if (response.data.setup_stage) {
            if (
                response.data.setup_stage.accounts &&
                response.data.setup_stage.settings
            ) {
                this.currentView =
                    this.views.findIndex((view) => view.name === 'complete') +
                    1;
            }

            if (
                response.data.setup_stage.accounts &&
                !response.data.setup_stage.settings
            ) {
                this.currentView =
                    this.views.findIndex((view) => view.name === 'settings') +
                    1;
            }
        }

        this.pleaseWait = false;
    },
});
</script>
