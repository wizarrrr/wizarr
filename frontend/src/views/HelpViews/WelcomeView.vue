<template>
    <PlexWelcomeView v-bind="$props" v-if="settings.server_type == 'plex'" @height="$emit('height')" />
    <JellyfinWelcomeView v-bind="$props" v-else-if="settings.server_type == 'jellyfin'" @height="$emit('height')" />
</template>

<script lang="ts">
import { mapState } from "pinia";
import { defineComponent } from "vue";
import { useServerStore } from "@/stores/server";

import PlexWelcomeView from "./PlexViews/WelcomeView.vue";
import JellyfinWelcomeView from "./JellyfinViews/WelcomeView.vue";

export default defineComponent({
    name: "CreateAccountView",
    components: {
        PlexWelcomeView,
        JellyfinWelcomeView,
    },
    computed: {
        ...mapState(useServerStore, ["settings"]),
    },
});
</script>
