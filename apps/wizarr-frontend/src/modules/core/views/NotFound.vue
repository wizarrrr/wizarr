<template>
    <div
        class="max-w-screen-xl flex flex-wrap items-center justify-center mx-auto md:h-screen"
    >
        <!-- Nav Bar for Authenticated Routes -->
        <AdminNavBar v-if="isAuthenticated" />
        <!-- Nav Bar for Unauthenticated Routes -->
        <DefaultNavBar button="Login" buttonLink="/login" v-else />

        <!-- Hero Section -->
        <section
            class="bg-gray-100 dark:bg-gray-900 px-2 md:px-4 lg:px-6 xl:px-8 mt-28 md:mt-0"
        >
            <div class="py-8 px-4 mx-auto max-w-screen-xl text-center lg:py-16">
                <div class="text-center">
                    <h1
                        class="mb-4 text-4xl font-extrabold tracking-tight leading-none text-gray-900 md:text-5xl lg:text-6xl dark:text-white"
                    >
                        404
                    </h1>
                    <p
                        class="mb-1 text-3xl tracking-tight font-bold text-gray-900 md:text-4xl dark:text-white"
                    >
                        {{ __("Something's missing.") }}
                    </p>
                    <p
                        class="mb-4 text-lg font-light text-gray-500 dark:text-gray-400"
                    >
                        {{
                            __(
                                "Sorry, we can't find that page. It doesn't seem to exist!",
                            )
                        }}
                    </p>
                </div>
                <div class="flex justify-center mt-6">
                    <DefaultButton v-if="isAuthenticated" to="/admin">{{
                        __('Go to Dashboard')
                    }}</DefaultButton>
                    <DefaultButton v-else to="/">{{
                        __('Go Home')
                    }}</DefaultButton>
                </div>
            </div>
        </section>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { mapActions } from 'pinia';

import AdminNavBar from '@/components/NavBars/AdminNavBar.vue';
import DefaultNavBar from '@/components/NavBars/DefaultNavBar.vue';
import DefaultButton from '@/components/Buttons/DefaultButton.vue';

export default defineComponent({
    name: 'NotFoundView',
    components: {
        DefaultNavBar,
        DefaultButton,
        AdminNavBar,
    },
    computed: {
        ...mapActions(useAuthStore, ['isAuthenticated']),
    },
});
</script>
