<template>
    <div class="flex flex-col space-y-4">
        <!-- Invitation Code -->
        <div class="flex flex-col space-y-2">
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

        <!-- Invitation Expiration -->
        <div class="flex flex-col space-y-2">
            <h2 class="text-sm text-gray-900 dark:text-white">
                {{ __('Invitation Details') }}
            </h2>
            <div class="flex flex-row space-x-2">
                <div
                    @click="invitationExpiredToggle"
                    class="w-full border border-gray-200 dark:border-gray-700 rounded py-2 px-4 text-xs text-gray-500 dark:text-gray-400 cursor-pointer"
                >
                    <span v-if="invitation.expires === null">{{
                        __('No expiration')
                    }}</span>
                    <span v-else-if="invitationExpired">{{
                        invitationExpiredHumanReadable
                    }}</span>
                    <span v-else>{{ invitationExpiredDateReadable }}</span>
                </div>
            </div>
        </div>

        <!-- Invitation Settings -->
        <div class="flex flex-col space-y-2">
            <h2 class="text-sm text-gray-900 dark:text-white">
                {{ __('Invitation Settings') }}
            </h2>
            <div class="flex flex-col space-y-2">
                <template v-for="item in quickList">
                    <span
                        :class="
                            item.value
                                ? 'bg-green-100 text-green-800 dark:bg-gray-700 dark:text-green-400 border-green-400'
                                : 'bg-red-100 text-red-800 dark:bg-gray-700 dark:text-red-400 border-red-400'
                        "
                        class="text-xs font-medium px-2.5 py-1 rounded border"
                    >
                        {{ item.text }}
                    </span>
                </template>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useClipboard } from '@vueuse/core';

import type { Invitation } from '@/types/api/invitations';
import type { Emitter, EventType } from 'mitt';

export default defineComponent({
    name: 'Invitation',
    props: {
        invitation: {
            type: Object as () => Invitation,
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
                    value: this.invitation.code,
                    active: true,
                },
                {
                    value: `${window.location.origin}/j/${this.invitation.code}`,
                    active: false,
                },
            ],
            invitationExpired: true,
            quickList: [
                {
                    text: 'Unlimited',
                    value: this.invitation.unlimited,
                },
                {
                    text: 'Allow Downloads',
                    value: this.invitation.plex_allow_sync,
                },
                {
                    text: 'Plex Home',
                    value: this.invitation.plex_home,
                },
            ],
            clipboard: useClipboard({
                legacy: true,
            }),
        };
    },
    computed: {
        invitationCodeValue(): string {
            return this.invitationCode.find((item) => item.active)!.value;
        },
        invitationExpiredHumanReadable(): string {
            if (this.$filter('isPast', this.invitation.expires)) {
                return this.__('Invitation expired %{s}', {
                    s: this.$filter('timeAgo', this.invitation.expires),
                });
            } else {
                return this.__('Invitation expires %{s}', {
                    s: this.$filter('timeAgo', this.invitation.expires),
                });
            }
        },
        invitationExpiredDateReadable(): string {
            return new Date(this.invitation.expires).toLocaleString();
        },
    },
    methods: {
        invitationCodeToggle() {
            this.invitationCode = this.invitationCode.map((item) => {
                item.active = !item.active;
                return item;
            });
        },
        invitationExpiredToggle() {
            this.invitationExpired = !this.invitationExpired;
        },
        invitationCodeCopy() {
            this.clipboard.copy(this.invitationCodeValue);
            this.$toast.info(this.__('Copied to clipboard'));
        },
    },
});
</script>
