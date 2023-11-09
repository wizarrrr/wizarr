<template>
    <div class="my-[-2rem] mx-[-2rem]">
        <!-- Header -->
        <div class="flex justify-between items-center flex-row dark:bg-gray-700 py-4 px-6">
            <DiscordLogo class="fill-gray-900 dark:fill-white" />
            <div class="text-gray-700 dark:text-white text-sm">
                <span class="font-bold">{{ totalMembersOnline }}</span>
                {{ __("Members Online") }}
            </div>
        </div>

        <!-- Members List -->
        <div class="flex flex-col space-y-2 h-[30vh] overflow-y-auto p-4 scrollbar-thin scrollbar-track-white dark:scrollbar-thumb-gray-900 dark:scrollbar-track-gray-800">
            <template v-for="member in members">
                <div class="flex items-center space-x-2">
                    <div class="relative w-[26px] h-[26px]">
                        <img :src="member.avatar_url" class="w-[26px] h-[26px] rounded-full" alt="Avatar" />
                        <span class="absolute bottom-[-2px] right-[-2px] w-3 h-3 rounded-full border-2 border-white dark:border-gray-800" :class="statusColor(member.status)"></span>
                    </div>
                    <span>{{ member.username }}</span>
                </div>
            </template>
        </div>

        <!-- Footer -->
        <div class="flex justify-between items-center flex-row dark:bg-gray-700 py-4 px-6">
            <div class="text-gray-900 dark:text-white text-sm">
                {{ __("Join our Discord") }}
            </div>
            <a :href="invite" target="_blank" rel="noopener noreferrer" class="text-gray-900 dark:text-white text-sm">
                {{ __("Join") }}
            </a>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useServerStore } from "@/stores/server";
import { mapState } from "pinia";

import DiscordLogo from "@/assets/img/discord.svg?component";

export interface Member {
    id: string;
    username: string;
    discriminator: string;
    avatar: null;
    status: string;
    avatar_url: string;
}

export type Members = Member[];

export default defineComponent({
    name: "Discord",
    components: {
        DiscordLogo,
    },
    data() {
        return {
            members: [] as Members,
            invite: "",
            interval: null as unknown as NodeJS.Timeout,
        };
    },
    computed: {
        totalMembersOnline() {
            return this.members.filter((member) => member.status === "online").length;
        },
        ...mapState(useServerStore, ["settings"]),
    },
    methods: {
        async loadWidgetAPI(guild: string) {
            // Load the Discord Widget API
            const response = await this.$rawAxios.get(`https://discord.com/api/guilds/${guild}/widget.json`).catch(() => {
                this.$toast.info("Unable to load Discord Widget, this is most likely due to too many requests.");
            });

            // Validate the response
            if (!response) return;

            // Set the widget data
            this.invite = response.data.instant_invite;
            this.members = response.data.members;
        },
        statusColor(status: string) {
            switch (status) {
                case "online":
                    return "bg-green-500";
                case "idle":
                    return "bg-yellow-500";
                case "dnd":
                    return "bg-red-500";
                case "offline":
                    return "bg-gray-500";
                default:
                    return "bg-gray-500";
            }
        },
    },
    mounted() {
        this.loadWidgetAPI(this.settings.server_discord_id!);
    },
});
</script>
