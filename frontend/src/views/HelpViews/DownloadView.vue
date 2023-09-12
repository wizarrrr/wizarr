<template>
    <PlexDownloadView v-bind="$props" v-if="settings.server_type == 'plex'" @height="$emit('height')" />
    <JellyfinDownloadView v-bind="$props" v-else-if="settings.server_type == 'jellyfin'" @height="$emit('height')" />
</template>

<script lang="ts">
import { mapState } from "pinia";
import { defineComponent } from "vue";
import { useServerStore } from "@/stores/server";

import PlexDownloadView from "./PlexViews/DownloadView.vue";
import JellyfinDownloadView from "./JellyfinViews/DownloadView.vue";

export default defineComponent({
    name: "DownloadView",
    components: {
        PlexDownloadView,
        JellyfinDownloadView,
    },
    computed: {
        ...mapState(useServerStore, ["settings"]),
    },
});
</script>
