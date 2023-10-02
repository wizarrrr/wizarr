<template>
    <div class="w-full h-full relative">
        <DefaultWidget :title="__('Contributors')" class="flex flex-col">
            <div class="flex flex-col space-between grow h-full">
                <div class="flex flex-col space-y-2">
                    <Transition name="fade" mode="out-in">
                        <div v-if="contributors" class="flex flex-col space-y-2">
                            <template v-for="contributor in contributors" :key="contributor.name">
                                <button @click="buttonLink(contributor.profile)" class="flex flex-row items-center justify-between p-2.5 rounded bg-gray-700 hover:bg-gray-600 transition duration-300">
                                    <h1 class="font-bold text-gray-400 dark:text-gray-300">{{ contributor.name }}</h1>
                                    <h1 class="font-bold text-gray-300 dark:text-gray-200">{{ formatCurrency(contributor.totalAmountDonated, contributor.currency) }}</h1>
                                </button>
                            </template>
                        </div>
                        <div v-else class="flex flex-col justify-center items-center space-y-1 py-4">
                            <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
                            <span class="text-gray-400">{{ __("No contributors found") }}</span>
                        </div>
                    </Transition>
                </div>
                <div class="flex flex-row grow items-end">
                    <FormKit @click="openLink" type="button" data-theme="secondary" :classes="{ outer: 'w-full', input: '!justify-center h-[35px] w-full' }">
                        {{ __("Support us") }}
                    </FormKit>
                </div>
            </div>
        </DefaultWidget>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import getSymbolFromCurrency from "currency-symbol-map";

import DefaultWidget from "@/widgets/templates/DefaultWidget.vue";

export type OpenCollectiveResponse = Array<{
    name: string;
    tier?: string;
    currency?: string;
    lastTransactionAt?: string;
    profile: string;
    totalAmountDonated?: number;
    role: "BACKER" | "ADMIN";
}>;

export default defineComponent({
    name: "ContributorsList",
    components: {
        DefaultWidget,
    },
    data() {
        return {
            contributors: null as OpenCollectiveResponse | null,
        };
    },
    methods: {
        buttonLink(link: string) {
            window.open(link, "_blank");
        },
        openLink() {
            window.open("https://opencollective.com/wizarr", "_blank");
        },
        formatCurrency(value?: number, currency?: string) {
            return `${getSymbolFromCurrency(currency ?? "USD")}${value}`;
        },
    },
    async mounted() {
        const response = await this.$axios.get<any, { data: OpenCollectiveResponse }>("https://opencollective.com/wizarr/members/all.json?limit=30", {
            method: "GET",
        });

        if (!response.data) {
            return;
        }

        const sorted = response.data
            .filter((contributor) => contributor.role === "BACKER")
            .sort((a, b) => new Date(b.lastTransactionAt!).getTime() - new Date(a.lastTransactionAt!).getTime())
            .slice(0, 4)
            .sort((a, b) => b.totalAmountDonated! - a.totalAmountDonated!);

        this.contributors = sorted;
    },
});
</script>
