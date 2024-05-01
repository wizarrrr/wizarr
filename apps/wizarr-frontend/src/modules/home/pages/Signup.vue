<template>
    <PlexSignup v-bind="$attrs" v-if="settings.server_type == 'plex'" />
    <JellyfinSignup
        v-bind="$attrs"
        v-else-if="settings.server_type == 'jellyfin'"
    />
    <EmbySignup
        v-bind="$attrs"
        v-else-if="settings.server_type == 'emby'"
    />
</template>

<script lang="ts">
import { mapState } from 'pinia';
import { defineComponent, defineAsyncComponent } from 'vue';
import { useServerStore } from '@/stores/server';

export default defineComponent({
    name: 'CreateAccountView',
    components: {
        PlexSignup: defineAsyncComponent(() => import('./Plex/Signup.vue')),
        JellyfinSignup: defineAsyncComponent(
            () => import('./Jellyfin/Signup.vue'),
        ),
        EmbySignup: defineAsyncComponent(
            () => import('./Emby/Signup.vue'),
        ),
    },
    computed: {
        ...mapState(useServerStore, ['settings']),
    },
});
</script>
