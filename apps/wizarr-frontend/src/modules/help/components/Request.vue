<template>
    <div class="flex flex-col space-y-4">
        <div>
            <h4 class="mb-3 text-xl font-bold dark:text-white">{{ __("Automatic Media Requests") }}</h4>
            <p class="mb-3 font-normal text-gray-700 dark:text-gray-400">
                {{ __("We are excited to offer you a wide selection of media to choose from. If you're having trouble finding something you like, don't worry! We have a user-friendly request system that can automatically search for the media you're looking for.") }}
            </p>
        </div>

        <ul class="space-y-2 text-left text-gray-500 dark:text-gray-400">
            <li class="flex items-center space-x-3">
                <i class="fas fa-check text-green-500 dark:text-green-400"></i>
                <span>{{ __("Request any available Movie or TV Show") }}</span>
            </li>
            <li class="flex items-center space-x-3">
                <i class="fas fa-check text-green-500 dark:text-green-400"></i>
                <span>{{ __("Media will be automatically downloaded to your library") }}</span>
            </li>
            <li class="flex items-center space-x-3">
                <i class="fas fa-check text-green-500 dark:text-green-400"></i>
                <span>{{ __("You can recieve notifications when your media is ready") }}</span>
            </li>
        </ul>

        <div class="flex justify-end pt-4">
            <FormKit type="button" suffixIcon="fas fa-external-link-alt" @click="openURL">
                {{ __("Check it Out") }}
            </FormKit>
        </div>
    </div>
</template>

<script lang="ts">
import type { Requests } from "@/types/api/request";
import { defineComponent, defineAsyncComponent } from "vue";

export default defineComponent({
    name: "Request",
    props: {
        requestURL: {
            type: Array as () => Requests,
            required: true,
        },
    },
    methods: {
        async selectURL() {
            const RequestsList = defineAsyncComponent(() => import("./RequestsList.vue"));

            this.$modal.openModal(RequestsList, {
                title: "Select Request Server",
                props: {
                    requestURLS: this.requestURL,
                },
            });
        },
        async openURL() {
            if (this.requestURL.length === 1) {
                window.open(this.requestURL[0].url, "_blank");
                return;
            }

            this.selectURL();
        },
    },
});
</script>
