<template>
    <PlexDownload v-bind="$props" v-if="settings.server_type == 'plex'" @height="$emit('height')" />
    <JellyfinDownload v-bind="$props" v-else-if="settings.server_type == 'jellyfin'" @height="$emit('height')" />
    <EmbyDownload v-bind="$props" v-else-if="settings.server_type == 'emby'" @height="$emit('height')" />
</template>

<script lang="ts">
import { mapState } from "pinia";
import { defineComponent, defineAsyncComponent } from "vue";
import { useServerStore } from "@/stores/server";

export default defineComponent({
    name: "Download",
    components: {
        PlexDownload: defineAsyncComponent(() => import("./Plex/Download.vue")),
        JellyfinDownload: defineAsyncComponent(() => import("./Jellyfin/Download.vue")),
        EmbyDownload: defineAsyncComponent(() => import("./Emby/Download.vue")),
    },
    computed: {
        ...mapState(useServerStore, ["settings"]),
    },
});
</script>
