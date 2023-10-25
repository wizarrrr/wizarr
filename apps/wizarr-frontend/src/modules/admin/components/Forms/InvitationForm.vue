<template>
    <div ref="invitationContainer" id="invitationContainer">
        <Transition name="fade" mode="out-in" :duration="{ enter: 200, leave: 200 }">
            <div v-if="!created && !failed">
                <FormKit type="form" name="inviteForm" id="inviteForm" @submit="createInvite" :actions="!eventBus" v-model="invitationData" :disabled="disabled" :submit-label="__('Create Invitation')" :submit-attrs="{ inputClass: 'w-full justify-center mt-2' }">
                    <div class="space-y-4">
                        <!-- Invite Code -->
                        <FormKit type="text" placeholder="XMFGEJI" label="Invitation Code" name="inviteCode" validation="length:6,6|uppercase" />

                        <!-- Select Expiration -->
                        <FormKit type="select" label="Invitation Expiration" name="expiration" :options="expirationOptions" />

                        <!-- Custom Expiration -->
                        <FormKit type="datepicker" v-if="invitationData.expiration == 'custom'" format="DD/MM/YYYY HH:mm" :sequence="['year', 'month', 'day', 'time']" :min-date="new Date()" label="Custom Expiration" name="customExpiration" />
                    </div>

                    <!-- ADVANCED OPTIONS -->
                    <button @click="advancedOptions = !advancedOptions" type="button" class="block text-sm font-medium text-secondary dark:text-primary my-2">
                        {{ __("Advanced Options") }}
                    </button>

                    <Collapse :when="advancedOptions" class="space-y-4">
                        <!-- Select Options -->
                        <FormKit type="checkbox" name="options" :options="checkboxOptions" />

                        <!-- Select Duration -->
                        <FormKit type="select" label="User Account Duration" name="duration" :options="durationOptions" />

                        <!-- Custom Duration -->
                        <FormKit type="datepicker" v-if="invitationData.duration == 'custom'" format="DD/MM/YYYY HH:mm" :sequence="['year', 'month', 'day', 'time']" :min-date="new Date()" label="Custom Duration" name="customDuration" />

                        <!-- SELECT SPECIFIC LIBRARIES -->
                        <!-- @vue-ignore -->
                        <FormKit type="dropdown" label="Select Libraries" placeholder="Select Libraries" name="libraries" :options="librariesOptions" multiple selection-appearance="tags" wrapper-class="mb-2" />
                    </Collapse>
                </FormKit>
            </div>
            <div v-else-if="created && !failed">
                <div @click="copyInviteLink">
                    <FormKit type="text" :value="inviteLink" readonly />
                </div>
                <div v-if="!eventBus" class="flex flex-row justify-end mt-4 space-x-2">
                    <DefaultButton theme="secondary" @click="createAnother">
                        {{ __("Create Another") }}
                    </DefaultButton>
                    <DefaultButton theme="primary" v-if="clipboard.isSupported" @click="copyInviteLink">
                        {{ __("Share") }}
                    </DefaultButton>
                </div>
            </div>
            <div v-else>
                <div class="flex flex-col items-center justify-center space-y-2 pb-6">
                    <i class="fa-solid fa-exclamation-circle text-black dark:text-gray-300 text-2xl"></i>
                    <span class="text-lg text-black dark:text-gray-300">
                        {{ __("Failed to create invitation") }}
                    </span>
                </div>
                <DefaultButton theme="secondary" @click="failed = false" class="w-full">
                    {{ __("Try Again") }}
                </DefaultButton>
            </div>
        </Transition>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState, mapActions } from "pinia";
import { useServerStore } from "@/stores/server";
import { useLibrariesStore } from "@/stores/libraries";
import { useInvitationStore } from "@/stores/invitations";
import { Collapse } from "vue-collapsed";
import { customAlphabet } from "nanoid";
import { useClipboard, useResizeObserver } from "@vueuse/core";

import DateInput from "@/components/Inputs/DateInput.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

import type { ToastID } from "vue-toastification/dist/types/types";
import type { Emitter, EventType } from "mitt";

export default defineComponent({
    name: "InvitationForm",
    components: {
        DateInput,
        Collapse,
        DefaultButton,
    },
    props: {
        eventBus: {
            type: Object as () => Emitter<Record<EventType, unknown>>,
            required: false,
        },
    },
    data() {
        return {
            clipboard: useClipboard(),
            created: false,
            failed: false,
            inviteCode: "",
            invitationData: {
                inviteCode: "",
                expiration: 1440 as number | null | "custom",
                customExpiration: "" as string,
                options: [] as string[],
                duration: "unlimited" as number | "unlimited" | "custom",
                customDuration: "" as string,
                libraries: [] as string[],
            },
            disabled: false,
            expirationOptions: [
                {
                    label: "1 Day",
                    value: 1440,
                },
                {
                    label: "1 Week",
                    value: 10080,
                },
                {
                    label: "1 Month",
                    value: 43800,
                },
                {
                    label: "6 Months",
                    value: 262800,
                },
                {
                    label: "1 Year",
                    value: 525600,
                },
                {
                    label: "Never",
                    value: null,
                },
                {
                    label: "Custom",
                    value: "custom",
                },
            ],
            durationOptions: [
                {
                    label: "Unlimited",
                    value: "unlimited",
                },
                {
                    label: "1 Day",
                    value: 1440,
                },
                {
                    label: "1 Week",
                    value: 10080,
                },
                {
                    label: "1 Month",
                    value: 43800,
                },
                {
                    label: "6 Months",
                    value: 262800,
                },
                {
                    label: "1 Year",
                    value: 525600,
                },
                {
                    label: "Custom",
                    value: "custom",
                },
            ],
            options: {
                jellyfin: {
                    unlimited: {
                        label: "Unlimited Invitation Usages",
                        value: "unlimited",
                    },
                },
                plex: {
                    unlimited: {
                        label: "Unlimited Invitation Usages",
                        value: "unlimited",
                    },
                    plex_home: {
                        label: "Allow Plex Home Access",
                        value: "plex_home",
                    },
                    plex_allow_sync: {
                        label: "Allow Plex Downloads",
                        value: "plex_allow_sync",
                    },
                },
            } as Record<string, Record<string, { label: string; value: string }>>,
            advancedOptions: false,
            clipboardToast: null as ToastID | null,
        };
    },
    methods: {
        ...mapActions(useLibrariesStore, ["getLibraries"]),
        ...mapActions(useInvitationStore, ["createInvitation"]),
        async createInvite() {
            const invitationData = this.invitationData;

            // Parse the data ready for the API
            const code = invitationData.inviteCode;
            const expires = invitationData.expiration == "custom" ? this.$filter("toMinutes", invitationData.customExpiration) : invitationData.expiration;
            const unlimited = invitationData.options.includes("unlimited");
            const plex_home = invitationData.options.includes("plex_home");
            const plex_allow_sync = invitationData.options.includes("plex_allow_sync");
            const duration = invitationData.duration == "custom" ? this.$filter("toMinutes", invitationData.customDuration) : invitationData.duration == "unlimited" ? null : invitationData.duration;
            const libraries = invitationData.libraries;

            const new_invitation = {
                code: code,
                expires: expires,
                unlimited: unlimited,
                plex_home: plex_home,
                plex_allow_sync: plex_allow_sync,
                duration: duration,
                specific_libraries: JSON.stringify(libraries),
            };

            const formData = new FormData();

            for (const key in new_invitation) {
                // @ts-ignore
                if (new_invitation[key] == null) continue;
                // @ts-ignore
                formData.append(key, new_invitation[key]);
            }

            // Create the invite
            const response = this.createInvitation(formData);

            if (response == null) {
                this.failed = true;
                return;
            }

            // Show the invite
            this.created = true;
            this.inviteCode = this.invitationData.inviteCode;
            this.$formkit.reset("inviteForm");
            this.invitationData.inviteCode = customAlphabet("ABCDEFGHIJKLMNOPQRSTUVWXYZ")(6);
            this.$emit("updateOptions", {
                title: this.__("Share Invitation"),
                buttons: [
                    {
                        text: this.__("Share"),
                        emit: "copyInviteLink",
                    },
                    {
                        text: this.__("Create Another"),
                        emit: "createAnother",
                        attrs: {
                            "data-theme": "secondary",
                        },
                    },
                ],
                disableCancelButton: true,
            });
        },
        createAnother() {
            this.created = false;
            this.$emit("updateOptions", {
                title: this.__("Create Invitation"),
                buttons: [
                    {
                        text: this.__("Create Invitation"),
                        emit: "createInvitation",
                    },
                ],
                disableCancelButton: false,
            });
        },
        copyInviteLink() {
            if (!this.clipboard.isSupported) return;
            this.clipboard.copy(this.inviteLink);
            if (this.clipboardToast != null)
                this.$toast.update(this.clipboardToast, "Copied to clipboard", {
                    timeout: 1000,
                });
            if (this.clipboardToast == null)
                this.clipboardToast = this.$toast.info("Copied to clipboard", {
                    onClose: () => (this.clipboardToast = null),
                });
        },
    },
    computed: {
        customExpiration() {
            return this.$filter("toMinutes", this.invitationData.customExpiration, true);
        },
        customDuration() {
            return this.$filter("toMinutes", this.invitationData.customDuration, true);
        },
        checkboxOptions() {
            return Object.keys(this.options[this.settings.server_type]).map((key) => {
                return this.options[this.settings.server_type][key];
            });
        },
        librariesOptions(): { label: string; value: string }[] {
            return this.libraries.map((library) => {
                return {
                    label: library.name,
                    value: library.id,
                };
            });
        },
        inviteLink() {
            return `${window.location.origin}/j/${this.inviteCode}`;
        },
        ...mapState(useLibrariesStore, ["libraries"]),
        ...mapState(useServerStore, ["settings"]),
    },
    watch: {
        "invitationData.inviteCode": {
            immediate: true,
            handler(inviteCode) {
                if (inviteCode.length >= 7) this.invitationData.inviteCode = inviteCode.slice(0, 6);
                this.invitationData.inviteCode = this.invitationData.inviteCode.replace(/[^a-zA-Z0-9]/g, "");
                this.invitationData.inviteCode = this.invitationData.inviteCode.toUpperCase();
            },
        },
        "settings.server_type": {
            immediate: true,
            handler(server_type) {
                if (!server_type) {
                    this.disabled = true;
                    this.$toast.error("Could not determine your server type, try refreshing the page.", {
                        closeOnClick: false,
                        draggable: false,
                        timeout: false,
                        closeButton: false,
                    });
                }
            },
        },
    },
    async mounted() {
        this.getLibraries();
        this.invitationData.inviteCode = customAlphabet("ABCDEFGHIJKLMNOPQRSTUVWXYZ")(6);
        this.invitationData.libraries = this.libraries.map((library) => library.id);

        this.eventBus?.on("createInvitation", this.createInvite);
        this.eventBus?.on("createAnother", this.createAnother);
        this.eventBus?.on("copyInviteLink", this.copyInviteLink);

        try {
            const invitationContainer = this.$refs.invitationContainer as HTMLElement;
            invitationContainer.style.width = invitationContainer.parentElement?.clientWidth + "px";

            useResizeObserver(invitationContainer.parentElement, (entry) => {
                invitationContainer.style.width = entry[0].contentRect.width + "px";
            });
        } catch {
            // Do nothing
        }
    },
});
</script>
