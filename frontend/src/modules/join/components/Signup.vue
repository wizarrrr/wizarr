<template>
    <PlexSignup v-bind="$props" v-if="settings.server_type == 'plex'" @height="$emit('height')" />
    <JellyfinSignup v-bind="$props" v-else-if="settings.server_type == 'jellyfin'" @height="$emit('height')" />
</template>

<script lang="ts">
import { mapState } from "pinia";
import { defineComponent, defineAsyncComponent } from "vue";
import { useServerStore } from "@/stores/server";

export default defineComponent({
    name: "CreateAccountView",
    components: {
        PlexSignup: defineAsyncComponent(() => import("./Plex/Signup.vue")),
        JellyfinSignup: defineAsyncComponent(() => import("./Jellyfin/Signup.vue")),
    },
    computed: {
        ...mapState(useServerStore, ["settings"]),
    },
});
</script>
