<template>
    <PlexSetupView v-bind="$props" v-if="settings.server_type == 'plex'" @height="$emit('height')" />
    <JellyfinSetupView v-bind="$props" v-else-if="settings.server_type == 'jellyfin'" @height="$emit('height')" />
</template>

<script lang="ts">
import { mapState } from "pinia";
import { defineComponent } from "vue";
import { useServerStore } from "@/stores/server";

import PlexSetupView from "./PlexViews/PlexSetupView.vue";
import JellyfinSetupView from "./JellyfinViews/JellyfinSetupView.vue";

export default defineComponent({
    name: "CreateAccountView",
    components: {
        PlexSetupView,
        JellyfinSetupView,
    },
    computed: {
        ...mapState(useServerStore, ["settings"]),
    },
});
</script>
