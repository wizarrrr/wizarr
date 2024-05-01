<template>
    <nav class="bg-white dark:bg-gray-900 relative w-full z-20 top-0 left-0 border-b border-gray-200 dark:border-gray-600">
        <div class="flex flex-row-reverse flex-column fixed right-0 m-3">
            <LanguageSelector iconClasses="text-base h-6 w-6" />
            <ThemeToggle iconClasses="text-base h-6 w-6" />
        </div>

        <div class="max-w-screen-xl flex flex-wrap items-center justify-between mx-auto p-4">
            <router-link to="/" class="flex items-center">
                <WizarrLogo class="mr-3" rounded />
                <span class="self-center text-2xl font-semibold whitespace-nowrap dark:text-white">{{ settings.server_name }}</span>
            </router-link>
            <div class="flex md:order-2">
                <DefaultButton :to="buttonLink" size="sm">
                    {{ button }}
                </DefaultButton>
            </div>
        </div>
    </nav>
</template>

<script lang="ts">
import { mapState } from 'pinia';
import { defineComponent } from "vue";
import { useServerStore } from '@/stores/server';
import { RouterLink } from "vue-router";

import WizarrLogo from "../WizarrLogo.vue";
import LanguageSelector from '@/components/Buttons/LanguageSelector.vue';
import ThemeToggle from '@/components/Buttons/ThemeToggle.vue';
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

export default defineComponent({
    name: "DefaultNavBar",
    components: {
        WizarrLogo,
        LanguageSelector,
        ThemeToggle,
        RouterLink,
        DefaultButton,
    },
    props: {
        title: {
            type: String,
            default: "Wizarr",
        },
        button: {
            type: String,
            default: "Homepage",
        },
        buttonLink: {
            type: String,
            default: "/",
        },
    },
    computed: {
        ...mapState(useServerStore, ['settings']),
    },
});
</script>
