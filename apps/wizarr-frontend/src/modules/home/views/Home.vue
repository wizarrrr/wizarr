<template>
    <div class="max-w-screen-xl flex flex-wrap items-center justify-between mx-auto md:h-screen">
        <!-- Nav Bar for Public Routes -->
        <DefaultNavBar :button="isAuthenticated ? 'Dashboard' : 'Login'" :buttonLink="isAuthenticated ? '/admin' : '/login'" />

        <!-- Hero Section -->
        <section class="bg-gray-100 dark:bg-gray-900 px-2 md:px-4 lg:px-6 xl:px-8 mt-28 md:mt-0">
            <div class="py-8 px-4 mx-auto max-w-screen-xl text-center lg:py-16">
                <h1 class="mb-4 text-4xl font-extrabold tracking-tight leading-none text-gray-900 md:text-5xl lg:text-6xl dark:text-white">{{ __("Welcome to") }} Wizarr</h1>
                <p class="mb-8 text-lg font-normal text-gray-500 sm:px-16 lg:px-48 dark:text-gray-400">
                    {{ __("Wizarr is a software tool that provides advanced user invitation and management capabilities for media servers such as Jellyfin, Emby, and Plex. With Wizarr, server administrators can easily invite new users and manage their access") }}
                </p>

                <p class="mb-8 text-sm font-bold text-gray-500 sm:px-16 lg:px-48 dark:text-gray-400">
                    {{ __("If you were sent here by a friend, please request access or if you have an invite code, please click Get Started!") }}
                </p>
                <div class="flex flex-col space-y-2 sm:flex-row sm:justify-center sm:space-y-0 sm:space-x-3">
                    <FormKit type="button" @click="$router.push('/join')" theme="primary" suffix-icon="fas fa-arrow-right">{{ __("Get Started") }}</FormKit>
                    <span class="inline-flex items-center text-gray-500 dark:text-gray-400 justify-center"> or </span>
                    <FormKit type="button" :disabled="true" data-theme="transparent">{{ __("Request Access") }}</FormKit>
                </div>
            </div>
        </section>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useAuthStore } from "@/stores/auth";
import { mapActions } from "pinia";

import DefaultNavBar from "@/components/NavBars/DefaultNavBar.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

export default defineComponent({
    name: "HomeView",
    components: {
        DefaultNavBar,
        DefaultButton,
    },
    computed: {
        ...mapActions(useAuthStore, ["isAuthenticated"]),
    },
});
</script>
