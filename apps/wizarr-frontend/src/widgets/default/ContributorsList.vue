<template>
    <div class="w-full h-full relative">
        <div class="flex flex-col justify-center grow h-full">
            <div class="flex flex-col space-y-2">
                <Transition name="fade" mode="out-in">
                    <div v-if="contributors" class="flex flex-col space-y-2">
                        <div class="space-y-2 divide-y divide-gray-200 rounded dark:divide-gray-700">
                            <!-- <div class="flex items-center justify-between pb-1">
                                <span class="text-lg font-bold truncate text-ellipsis">{{ __("Recent Contributors") }}</span>
                                <FormKit
                                    type="button"
                                    @click="openLink"
                                    data-theme="transparent"
                                    :classes="{
                                        input: '!py-1 truncate text-ellipsis',
                                    }">
                                    {{ __("Support Us") }}
                                </FormKit>
                            </div>
                            <template v-if="contributors.length > 0">
                                <div v-for="contributor in contributors" class="flex items-center justify-between pt-2">
                                    <div>
                                        <div class="text-sm font-bold text-gray-500 dark:text-gray-300 truncate text-ellipsis">
                                            {{ contributor.name }}
                                        </div>
                                        <div class="text-xs text-gray-600 dark:text-gray-400 truncate text-ellipsis">
                                            {{ $filter("timeAgo", new Date(contributor.lastTransactionAt ?? Date.now())) }}
                                        </div>
                                    </div>
                                    <div class="text-xs font-bold text-gray-500 dark:text-gray-200">
                                        {{ formatCurrency(contributor.totalAmountDonated, contributor.currency) }}
                                    </div>
                                </div>
                            </template>
                            <template v-else>
                                <div class="flex flex-col justify-center items-center space-y-1 py-4">
                                    <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
                                    <span class="text-gray-400">{{ __("No contributors found") }}</span>
                                </div>
                            </template> -->

                            <div class="flex flex-col justify-center items-center space-y-1 py-4">
                                <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
                                <span class="text-gray-400 text-center">{{ __("We currently do not have access to Open Collective. If you are making payments, please cancel them.") }}</span>
                            </div>
                        </div>
                    </div>
                    <div v-else class="flex flex-col space-y-2">
                        <div class="space-y-4 divide-y divide-gray-200 rounded animate-pulse dark:divide-gray-700">
                            <div v-for="i in 5" class="flex items-center justify-between pt-4">
                                <div>
                                    <div class="h-2.5 bg-gray-300 rounded-full dark:bg-gray-600 w-24 mb-2.5"></div>
                                    <div class="w-32 h-2 bg-gray-200 rounded-full dark:bg-gray-700"></div>
                                </div>
                                <div class="h-2.5 bg-gray-300 rounded-full dark:bg-gray-700 w-12"></div>
                            </div>
                        </div>
                    </div>
                </Transition>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import getSymbolFromCurrency from "currency-symbol-map";

export type OpenCollectiveResponse = Array<{
    name: string;
    tier?: string;
    currency?: string;
    lastTransactionAt: string;
    profile: string;
    totalAmountDonated?: number;
    role: "BACKER" | "ADMIN";
}>;

export default defineComponent({
    name: "ContributorsList",
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
    async created() {
        const response = await this.$axios
            .get<any, { data: OpenCollectiveResponse }>("https://opencollective.com/wizarr/members/all.json?limit=30", {
                method: "GET",
            })
            .catch(() => null);

        if (!response?.data) {
            return;
        }

        const sorted = response.data
            .filter((contributor) => (contributor.totalAmountDonated ?? 0) > 0)
            .filter((contributor) => contributor.name !== "Guest")
            .reduce((acc, contributor) => ((existing) => (existing ? acc.map((item) => (item.profile === contributor.profile ? { ...item } : item)) : [...acc, contributor]))(acc.find((item) => item.profile === contributor.profile)), [] as OpenCollectiveResponse)
            .sort((a, b) => new Date(b.lastTransactionAt).getTime() - new Date(a.lastTransactionAt).getTime())
            .slice(0, 5);

        // Blue "Top Contributors" text
        console.log("%cTop Contributors", "color: #2196f3; font-size: 1.5rem; font-weight: bold;");
        console.log("%cThank you for supporting Wizarr!", "color: #2196f3; font-size: 1.2em; font-weight: bold;");

        // Console log the contributors with the most recent at the top and color
        Object.entries(sorted).forEach(([index, contributor]) => {
            console.log(`%c${parseInt(index) + 1}. ${contributor.name} - ${this.formatCurrency(contributor.totalAmountDonated, contributor.currency)}`, "color: #4caf50");
        });

        this.contributors = sorted;
    },
});
</script>
