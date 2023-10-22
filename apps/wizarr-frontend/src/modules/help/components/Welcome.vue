<template>
    <PlexWelcome
        v-bind="$props"
        v-if="settings.server_type == 'plex'"
        @height="$emit('height')"
    />
    <JellyfinWelcome
        v-bind="$props"
        v-else-if="settings.server_type == 'jellyfin'"
        @height="$emit('height')"
    />
</template>

<script lang="ts">
import { mapState } from 'pinia';
import { defineComponent, defineAsyncComponent } from 'vue';
import { useServerStore } from '@/stores/server';

export default defineComponent({
    name: 'Welcome',
    components: {
        PlexWelcome: defineAsyncComponent(() => import('./Plex/Welcome.vue')),
        JellyfinWelcome: defineAsyncComponent(
            () => import('./Jellyfin/Welcome.vue'),
        ),
    },
    computed: {
        ...mapState(useServerStore, ['settings']),
    },
});
</script>
