<template>
    <Transition name="fade" mode="out-in" :duration="{ enter: 200, leave: 200 }">
        <div v-if="!created && !failed">
            <FormKit type="form" name="inviteForm" id="inviteForm" @submit="createInvite" v-model="inviteData" :disabled="disabled" :submit-label="__('Create Invitation')" :submit-attrs="{ inputClass: 'w-full justify-center mt-2' }">
                <div class="space-y-4">
                    <!-- Invite Code -->
                    <FormKit type="text" placeholder="XMFGEJI" label="Invite Code" name="inviteCode" validation="length:6,6|uppercase" />

                    <!-- Select Expiration -->
                    <FormKit type="select" label="Expiration" name="expiration" :options="expirationOptions" />

                    <!-- Custom Expiration -->
                    <FormKit type="datepicker" v-if="inviteData.expiration == 'custom'" format="DD/MM/YYYY HH:mm" :sequence="['year', 'month', 'day', 'time']" :min-date="new Date()" label="Custom Expiration" name="customExpiration" />
                </div>

                <!-- ADVANCED OPTIONS -->
                <button @click="advancedOptions = !advancedOptions" type="button" class="block mb-2 text-sm font-medium text-secondary dark:text-primary mt-2 mb-2">
                    {{ __("Advanced Options") }}
                </button>

                <Collapse :when="advancedOptions" class="space-y-4">
                    <!-- Select Options -->
                    <FormKit type="checkbox" name="options" :options="checkboxOptions" />

                    <!-- Select Duration -->
                    <FormKit type="select" label="Duration" name="duration" :options="durationOptions" />

                    <!-- Custom Duration -->
                    <FormKit type="datepicker" v-if="inviteData.duration == 'custom'" format="DD/MM/YYYY HH:mm" :sequence="['year', 'month', 'day', 'time']" :min-date="new Date()" label="Custom Duration" name="customDuration" />

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
            <div class="flex flex-row justify-end mt-4 space-x-2">
                <DefaultButton theme="secondary" @click="created = false">
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
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState, mapActions } from "pinia";
import { useServerStore } from "@/stores/server";
import { useLibrariesStore } from "@/stores/libraries";
import { useInvitationStore } from "@/stores/invitations";
import { Collapse } from "vue-collapsed";
import { customAlphabet } from "nanoid";
import { useClipboard } from "@vueuse/core";

import DefaultInput from "@/components/Inputs/DefaultInput.vue";
import SelectInput from "@/components/Inputs/SelectInput.vue";
import DateInput from "@/components/Inputs/DateInput.vue";
import DefaultButton from "../Buttons/DefaultButton.vue";

import type { ToastID } from "vue-toastification/dist/types/types";

export default defineComponent({
    name: "InviteView",
    components: {
        DefaultInput,
        SelectInput,
        DateInput,
        Collapse,
        DefaultButton,
    },
    data() {
        return {
            clipboard: useClipboard(),
            created: false,
            failed: false,
            inviteCode: "",
            inviteData: {
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
                        label: "Unlimited Usages",
                        value: "unlimited",
                    },
                },
                plex: {
                    unlimited: {
                        label: "Unlimited Usages",
                        value: "unlimited",
                    },
                    plex_home: {
                        label: "Allow Home Access",
                        value: "plex_home",
                    },
                    plex_allow_sync: {
                        label: "Allow Downloads",
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
        async createInvite(inviteData: typeof this.inviteData) {
            // Parse the data ready for the API
            const code = inviteData.inviteCode;
            const expires = inviteData.expiration == "custom" ? this.$filter("toMinutes", inviteData.customExpiration) : inviteData.expiration;
            const unlimited = inviteData.options.includes("unlimited");
            const plex_home = inviteData.options.includes("plex_home");
            const plex_allow_sync = inviteData.options.includes("plex_allow_sync");
            const duration = inviteData.duration == "custom" ? this.$filter("toMinutes", inviteData.customDuration) : inviteData.duration == "unlimited" ? null : inviteData.duration;
            const libraries = inviteData.libraries;

            // Create the invite
            const formData = new FormData();
            formData.append("code", code);
            if (expires) formData.append("expires", expires.toString());
            formData.append("unlimited", unlimited.toString());
            formData.append("plex_home", plex_home.toString());
            formData.append("plex_allow_sync", plex_allow_sync.toString());
            if (duration) formData.append("duration", duration.toString());
            formData.append("specific_libraries", JSON.stringify(libraries));

            // Create the invite
            const response = this.createInvitation(formData);

            if (response == null) {
                this.failed = true;
                return;
            }

            // Show the invite
            this.created = true;
            this.inviteCode = this.inviteData.inviteCode;
            this.$formkit.reset("inviteForm");
            this.inviteData.inviteCode = customAlphabet("ABCDEFGHIJKLMNOPQRSTUVWXYZ")(6);
        },
        copyInviteLink() {
            if (!this.clipboard.isSupported) return;
            this.clipboard.copy(this.inviteLink);
            if (this.clipboardToast != null) this.$toast.update(this.clipboardToast, "Copied to clipboard", { timeout: 1000 });
            if (this.clipboardToast == null) this.clipboardToast = this.$toast.info("Copied to clipboard", { onClose: () => (this.clipboardToast = null) });
        },
    },
    computed: {
        customExpiration() {
            return this.$filter("toMinutes", this.inviteData.customExpiration, true);
        },
        customDuration() {
            return this.$filter("toMinutes", this.inviteData.customDuration, true);
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
        "inviteData.inviteCode": {
            immediate: true,
            handler(inviteCode) {
                if (inviteCode.length >= 7) this.inviteData.inviteCode = inviteCode.slice(0, 6);
                this.inviteData.inviteCode = this.inviteData.inviteCode.replace(/[^a-zA-Z0-9]/g, "");
                this.inviteData.inviteCode = this.inviteData.inviteCode.toUpperCase();
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
        this.inviteData.inviteCode = customAlphabet("ABCDEFGHIJKLMNOPQRSTUVWXYZ")(6);
        this.inviteData.libraries = this.libraries.map((library) => library.id);
    },
});
</script>
