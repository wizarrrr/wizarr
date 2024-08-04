<template>
    <MdPreview v-model="value" :theme="currentTheme" :language="language" :sanitize="sanitize" />
    <!-- Bottom Bar -->
    <div class="flex flex-row justify-between pt-4">
        <span class="flex justify-end items-center">
            <a .href="settings.server_url_override ?? settings.server_url" class="bg-primary hover:bg-primary_hover focus:outline-none text-white font-medium rounded dark:bg-primary dark:hover:bg-primary_hover px-5 py-2.5 text-sm whitespace-nowrap flex items-center justify-center relative">
                <span v-if="settings.server_type == 'plex'">{{ __("Open Plex") }}</span>
                <span v-else-if="settings.server_type == 'jellyfin'">{{ __("Open Jellyfin") }}</span>
                <span v-else-if="settings.server_type == 'emby'">{{ __("Open Emby") }}</span>
                <i class="fas fa-external-link-alt ml-2"></i> </a
        ></span>
        <span class="flex justify-end items-center">
            <a .href="downloadURL" target="_blank" class="text-sm font-medium text-primary flex flex-row">
                {{ __("Other Download") }}
                <i class="fas fa-download ml-2 mt-[2px]"></i>
            </a>
        </span>
    </div>
</template>

<script lang="ts">
import { mapState } from "pinia";
import { defineComponent, type PropType } from "vue";
import { MdPreview } from "md-editor-v3";
import { useServerStore } from "@/stores/server";
import { useThemeStore } from "@/stores/theme";
import { useLanguageStore } from "@/stores/language";

export default defineComponent({
    name: "Download",
    components: {
        MdPreview,
    },
    props: {
        value: {
            type: String,
            required: true,
        },
        sanitize: {
            type: Function as PropType<(html: string) => string>,
            default: (html: string) => html,
        },
    },
    computed: {
        downloadURL() {
            switch (this.settings.server_type) {
                case "plex":
                    return "https://www.plex.tv/en-gb/media-server-downloads/#plex-app";
                case "jellyfin":
                    return "https://jellyfin.org/downloads";
                case "emby":
                    return "https://emby.media/download.html";
                default:
                    return "";
            }
        },
        ...mapState(useServerStore, ["settings"]),
        ...mapState(useThemeStore, ["currentTheme"]),
        ...mapState(useLanguageStore, ["language"]),
    },
});
</script>
