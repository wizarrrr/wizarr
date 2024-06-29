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
                <template v-for="(data, label) in checkboxOptions[0]" :key="label">
                    <FormKit type="checkbox" :label="data.label" :value="data.value" disabled />
                </template>

                <template v-for="(data, label) in selectsOptions[0]" :key="label">
                    <FormKit type="select" :label="data.label" :name="label" :options="data.options" :value="data.value" disabled />
                </template>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapState, mapActions } from "pinia";
import { useServerStore } from "@/stores/server";
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
                    value: `${window.location.origin}/i/${this.invitation.code}`,
                    active: false,
                },
            ],
            invitationExpired: true,
            checkboxes: {
                jellyfin: {
                    unlimited: {
                        label: "Unlimited Invitation Usages",
                        value: this.invitation.unlimited,
                    },
                    live_tv: {
                        label: "Access to Live TV",
                        value: this.invitation.live_tv,
                    },
                    hide_user: {
                        label: "Hide User from the Login Page",
                        value: this.invitation.hide_user,
                    },
                    allow_download: {
                        label: "Allow User to Download Content",
                        value: this.invitation.allow_download,
                    },
                },
                emby: {
                    unlimited: {
                        label: "Unlimited Invitation Usages",
                        value: this.invitation.unlimited,
                    },
                    live_tv: {
                        label: "Access to Live TV",
                        value: this.invitation.live_tv,
                    },
                    hide_user: {
                        label: "Hide User from the Login Page",
                        value: this.invitation.hide_user,
                    },
                    allow_download: {
                        label: "Allow User to Download Content",
                        value: this.invitation.allow_download,
                    },
                },
                plex: {
                    unlimited: {
                        label: "Unlimited Invitation Usages",
                        value: this.invitation.unlimited,
                    },
                    plex_allow_sync: {
                        label: "Allow Plex Downloads",
                        value: this.invitation.plex_allow_sync,
                    },
                },
            } as Record<string, Record<string, { label: string; value: boolean }>>,
            selects: {
                jellyfin: {
                    sessions: {
                        label: "Maximum Number of Simultaneous Logins",
                        value: this.invitation.sessions,
                        options: {
                            0: "No Limit",
                            1: "1 Session",
                            2: "2 Sessions",
                            3: "3 Sessions",
                            4: "4 Sessions",
                            5: "5 Sessions",
                            6: "6 Sessions",
                            7: "7 Sessions",
                            8: "8 Sessions",
                            9: "9 Sessions",
                            10: "10 Sessions",
                        },
                    },
                },
                emby: {
                    sessions: {
                        label: "Maximum Number of Simultaneous Streams",
                        value: this.invitation.sessions,
                        options: {
                            0: "No Limit",
                            1: "1 Stream",
                            2: "2 Streams",
                            3: "3 Streams",
                            4: "4 Streams",
                            5: "5 Streams",
                            6: "6 Streams",
                            7: "7 Streams",
                            8: "8 Streams",
                            9: "9 Streams",
                            10: "10 Streams",
                        },
                    },
                },
            } as Record<string, Record<string, { label: string; value: number, options: Record<number, string> }>>,
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
        checkboxOptions() {
            if (!this.checkboxes[this.settings.server_type]) return [];

            return Object.keys(this.checkboxes[this.settings.server_type]).map((key) => {
                return this.checkboxes[this.settings.server_type];
            });
        },
        selectsOptions() {
            if (!this.selects[this.settings.server_type]) return [];

            return Object.keys(this.selects[this.settings.server_type]).map((key) => {
                return this.selects[this.settings.server_type];
            });
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
