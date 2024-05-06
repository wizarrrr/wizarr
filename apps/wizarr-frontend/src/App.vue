<template>
    <vue-progress-bar />
    <FullPageLoading v-if="fullPageLoading" />
    <RouterView v-else />
    <Offline />
    <ReloadPrompt />
    <WidgetModalContainer />
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapWritableState, mapState, mapActions } from "pinia";
import { useThemeStore } from "@/stores/theme";
import { useServerStore } from "./stores/server";
import { useAuthStore } from "@/stores/auth";
import { useLanguageStore } from "@/stores/language";
import { useProgressStore } from "./stores/progress";
import { useGettext, type Language } from "vue3-gettext";
import { container as WidgetModalContainer } from "jenesius-vue-modal";

import type { ToastID } from "vue-toastification/dist/types/types";

import Offline from "@/components/Offline.vue";
import FullPageLoading from "@/components/Loading/FullPageLoading.vue";
import BadBackend from "@/components/Toasts/BadBackend.vue";
import UpdateAvailable from "@/components/Toasts/UpdateAvailable.vue";
import DefaultToast from "@/components/Toasts/DefaultToast.vue";
import ReloadPrompt from "@/components/ReloadPrompt.vue";

export default defineComponent({
    name: "App",
    components: {
        Offline,
        FullPageLoading,
        ReloadPrompt,
        WidgetModalContainer,
    },
    data() {
        return {
            gettext: null as Language | null,
            connectionToast: null as ToastID | null,
        };
    },
    computed: {
        ...mapState(useThemeStore, ["theme"]),
        ...mapState(useLanguageStore, ["language"]),
        ...mapWritableState(useProgressStore, ["progress", "fullPageLoading"]),
        ...mapActions(useAuthStore, ["isAuthenticated"]),
    },
    methods: {
        ...mapActions(useThemeStore, ["updateTheme"]),
        ...mapActions(useLanguageStore, ["updateLanguage", "updateAvailableLanguages"]),
        ...mapActions(useServerStore, ["setServerData"]),
        async backendTest() {
            while (true) {
                const serverData = await this.$axios
                    .get("/api/server")
                    .then((response) => response.data)
                    .catch(() => undefined);
                if (serverData) {
                    this.$toast.dismiss(this.connectionToast as ToastID);
                    this.$toast.success(DefaultToast("Connection Online", "Connection to backend established."));
                    this.setServerData(serverData);
                    break;
                }
                await new Promise((resolve) => setTimeout(resolve, 5000));
            }
        },
    },
    watch: {
        theme: {
            immediate: true,
            handler(theme) {
                this.updateTheme(theme);
            },
        },
        language: {
            immediate: true,
            handler(language) {
                if (this.gettext !== null) {
                    this.updateLanguage(this.gettext, language);
                }
            },
        },
        progress: {
            immediate: true,
            handler(progress) {
                if (progress) this.$Progress.start();
                else this.$Progress.finish();
            },
        },
    },
    beforeCreate() {
        // Start the progress bar before the app is created
        this.$Progress.start();
    },
    async mounted() {
        // Initialize gettext
        this.gettext = useGettext();

        // Set the language and available languages
        this.updateLanguage(this.gettext, this.language);
        this.updateAvailableLanguages(this.gettext);

        // Set the theme
        this.updateTheme(this.theme);

        // Get the server data
        const serverData = await this.$axios
            .get("/api/server")
            .then((response) => response.data)
            .catch(() => undefined);

        // If health data or server data is undefined, show error toast
        if (!serverData) {
            this.connectionToast = this.$toast.error(BadBackend, {
                timeout: false,
                closeButton: false,
                draggable: false,
                closeOnClick: false /* onClick: this.showServerURLModal */,
            });
            this.backendTest();
        }

        // If setup is required, redirect to setup page if current route is not setup page
        if (serverData?.setup_required && this.$router.currentRoute.value.name !== "setup") this.$router.push("/setup");
        if (!serverData?.setup_required && this.$router.currentRoute.value.name === "setup") this.$router.push("/");

        // If update is available, show update available toast to authenticated users
        if (serverData?.update_available && this.isAuthenticated) {
            this.$toast.info(UpdateAvailable, {
                timeout: false,
                draggable: false,
                closeOnClick: false,
            });
        }

        // Set the server data
        this.setServerData(serverData);

        // Finish the progress bar
        this.$Progress.finish();
        this.fullPageLoading = false;
    },
});
</script>
