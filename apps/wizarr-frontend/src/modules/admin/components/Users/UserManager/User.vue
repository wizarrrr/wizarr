<template>
    <div class="flex flex-col space-y-4">
        <!-- User Information -->
        <div class="flex flex-row space-x-3">
            <div
                class="flex-shrink-0 h-[45px] w-[45px] rounded bg-gray-50 overflow-hidden"
            >
                <img
                    :src="'https://ui-avatars.com/api/?uppercase=true&background=' + server_color + '&color=fff&name=' + user.username + '&length=1'"
                    class="w-full h-full object-cover object-center"
                    alt="Profile Picture"
                />
            </div>
            <div class="flex flex-col items-start justify-center mt-[-2px]">
                <span
                    class="text-lg text-bold text-gray-500 dark:text-gray-400"
                >
                    {{ user.username }}
                </span>
                <span class="text-xs text-gray-500 dark:text-gray-400">
                    {{ user.email }}
                </span>
            </div>
        </div>

        <!-- Spacer -->
        <hr class="border-gray-200 dark:border-gray-700" />

        <!-- Invitation Code -->
        <div class="flex flex-col space-y-2" v-if="user.code">
            <h2 class="text-sm text-gray-900 dark:text-white">
                {{ __('Invitation Code') }}
            </h2>
            <div class="flex flex-row space-x-2">
                <div
                    @click="invitationCodeToggle"
                    class="w-full border border-gray-200 dark:border-gray-700 rounded py-2 px-4 text-xs text-gray-500 dark:text-gray-400 cursor-pointer"
                >
                    <span>{{ invitationCodeValue }}</span>
                </div>
                <FormKit
                    type="button"
                    @click="invitationCodeCopy"
                    data-theme="secondary"
                    :classes="{ input: '!bg-secondary !px-3.5 h-[36px]' }"
                >
                    <i class="fa-solid fa-clipboard"></i>
                </FormKit>
            </div>
        </div>

        <!-- User Expiration -->
        <div class="flex flex-col space-y-2">
            <h2 class="text-sm text-gray-900 dark:text-white">
                {{ __('User Expiration') }}
            </h2>
            <div class="flex flex-row space-x-2">
                <div
                    @click="userExpiredToggle"
                    class="w-full border border-gray-200 dark:border-gray-700 rounded py-2 px-4 text-xs text-gray-500 dark:text-gray-400 cursor-pointer"
                >
                    <span v-if="user.expires === null">{{
                        __('No expiration')
                    }}</span>
                    <span v-else-if="userExpired">{{
                        userExpiredHumanReadable
                    }}</span>
                    <span v-else>{{ userExpiredDateReadable }}</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapState } from "pinia";
import { useServerStore } from "@/stores/server";

import type { User } from '@/types/api/users';
import type { Emitter, EventType } from 'mitt';
import { useClipboard } from '@vueuse/core/index.mjs';

export default defineComponent({
    name: 'User',
    props: {
        user: {
            type: Object as () => User,
            required: true,
        },
        eventBus: {
            type: Object as () => Emitter<Record<EventType, unknown>>,
            required: false,
        },
    },
    data() {
        return {
            invitationCode: [
                {
                    value: this.user.code,
                    active: true,
                },
                {
                    value: `${window.location.origin}/i/${this.user.code}`,
                    active: false,
                },
            ],
            userExpired: true,
            clipboard: useClipboard({
                legacy: true,
            }),
        };
    },
    computed: {
        invitationCodeValue(): string {
            return this.invitationCode.find((item) => item.active)!.value!;
        },
        userExpiredHumanReadable() {
            if (this.$filter('isPast', this.user.expires!)) {
                return this.__('User expired %{s}', {
                    s: this.$filter('timeAgo', this.user.expires!),
                });
            } else {
                return this.__('User expires %{s}', {
                    s: this.$filter('timeAgo', this.user.expires!),
                });
            }
        },
        userExpiredDateReadable() {
            return new Date(this.user.expires!).toLocaleString();
        },
        server_color() {
            // change the color of the profile picture border based on the server type
            switch (this.settings.server_type) {
                case "jellyfin":
                    return "b06ac8";
                case "emby":
                    return "74c46e";
                case "plex":
                    return "ffc933";
                default:
                    return "999999";
            }
        },
        ...mapState(useServerStore, ["settings"]),
    },
    methods: {
        invitationCodeToggle() {
            this.invitationCode = this.invitationCode.map((item) => {
                item.active = !item.active;
                return item;
            });
        },
        userExpiredToggle() {
            this.userExpired = !this.userExpired;
        },
        invitationCodeCopy() {
            this.clipboard.copy(this.invitationCodeValue);
            this.$toast.info(this.__('Copied to clipboard'));
        },
    },
});
</script>
