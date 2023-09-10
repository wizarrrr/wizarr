<template>
    <div>
        <div class="flex justify-center items-center flex-col mt-12 mb-3 space-y-6">
            <WizarrLogo rounded class="w-[150px] h-[150px]" />
            <h1 class="text-2xl font-semibold text-center text-gray-900 dark:text-white">{{ __("Type in your invite code to %{server_name} server!", { server_name: settings.server_name }) }}</h1>
        </div>
        <section>
            <div class="flex flex-col items-center justify-center md:container py-8 mx-auto">
                <div class="w-full md:w-1/2 lg:w-1/3 bg-white rounded shadow dark:border dark:bg-gray-800 dark:border-gray-700 overflow-hidden">
                    <div class="p-6 space-y-4 md:space-y-6 sm:p-8 text-gray-900 dark:text-white">
                        <h1 class="relative text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
                            {{ __("Join the %{server_type} Server", { server_type: serverType }) }}
                        </h1>
                        <JoinForm />
                    </div>
                </div>
            </div>
        </section>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState } from "pinia";
import { useServerStore } from "@/stores/server";

import WizarrLogo from "@/components/WizarrLogo.vue";
import JoinForm from "@/components/Forms/JoinForm.vue";

export default defineComponent({
    name: "JoinView",
    components: {
        WizarrLogo,
        JoinForm,
    },
    computed: {
        serverType() {
            switch (this.settings.server_type) {
                case "plex":
                    return "Plex";
                case "jellyfin":
                    return "Jellyfin";
                default:
                    return "Wizarr";
            }
        },
        ...mapState(useServerStore, ["settings"]),
    },
});
</script>
