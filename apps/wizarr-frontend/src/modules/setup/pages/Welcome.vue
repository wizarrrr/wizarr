<template>
    <div class="flex flex-col justify-center items-center space-y-4">
        <div class="text-center">
            <!-- Title -->
            <h1 class="text-2xl font-semibold">
                {{ __('Welcome to Wizarr') }}
            </h1>

            <!-- Subtitle -->
            <div class="text-gray-500 dark:text-gray-400">
                <h2 class="text-xs">
                    Automatic User Invitation System for<br />
                    Plex and Jellyfin
                </h2>
            </div>

            <hr class="my-4 border-gray-200 dark:border-gray-700" />

            <!-- Description -->
            <p class="text-base text-center">
                Wizarr is a powerful tool that makes it easy to manage user
                invitations for your Plex or Jellyfin media server. With
                Wizarr, you can create unique invitation links to share with
                users, and they will be automatically invited to your server
                once they click on the link.
            </p>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
    name: 'WelcomeView',
});
</script>
