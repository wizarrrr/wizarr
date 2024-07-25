<template>
    <div class="flex flex-col">
        <div class="space-y-6">
            <template v-for="(section, index) in settingsSections">
                <div :id="`settingsContainer${index}`">
                    <!-- Sections Title -->
                    <div class="settings-section" v-if="!(sectionDisabled(section) && !is_beta)">
                        <div class="flex flex-col">
                            <div class="text-lg font-bold leading-tight tracking-tight text-gray-900 md:text-xl dark:text-white">
                                {{ __(section.title) }}
                            </div>
                            <div class="text-xs font-semibold leading-tight tracking-tight text-gray-900 md:text-sm dark:text-gray-400">
                                {{ __(section.description) }}
                            </div>
                        </div>
                    </div>

                    <!-- Settings Grid -->
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
                        <template v-for="page in section.pages">
                            <template v-if="!(page.disabled && !is_beta)">
                                <SettingsButton :title="page.title" :description="page.description" :icon="page.icon" :url="page.url" :disabled="page.disabled" :modal="page.modal" />
                            </template>
                        </template>
                    </div>
                </div>
            </template>

            <div class="text-center text-gray-500 dark:text-gray-400 pb-2" v-if="settingsSections.length === 0">
                {{ __("No settings matched your search.") }}
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useUserStore } from "@/stores/user";
import { mapState } from "pinia";
import { useSettingsStore } from "@/stores/settings";
import { useServerStore } from "@/stores/server";

import SettingsTemplate from "@/templates/SettingsTemplate.vue";
import SettingsButton from "@/components/Buttons/SettingsButton.vue";

// These methods look confusing, because they are. I'm sorry ;P

export default defineComponent({
    name: "SettingsView",
    components: {
        SettingsTemplate,
        SettingsButton,
    },
    methods: {
        mapSections<K>(section: K & { pages: Partial<{ title: string; description: string }>[] }) {
            return {
                ...section,
                pages: section.pages.filter((page) => {
                    return page?.title?.toLowerCase().includes(this.search.toLowerCase()) ?? page?.description?.toLowerCase().includes(this.search.toLowerCase());
                }),
            };
        },
        filterSections<K>(section: K & { pages: Partial<{ title: string }>[] }) {
            return section.pages.length > 0;
        },
        mapRoles<K>(
            section: K & {
                roles?: string[];
                pages: Partial<{ roles?: string[] }>[];
            },
        ) {
            return {
                ...section,
                pages: section.pages.filter((page) => {
                    if ((this.user?.role ?? "user") === "admin") return true;
                    if (!page?.roles) return section?.roles?.includes(this.user?.role ?? "user");
                    return page?.roles?.includes(this.user?.role ?? "user");
                }),
            };
        },
        sectionDisabled<K>(section: K & { pages: Partial<{ disabled?: boolean }>[] }) {
            return section.pages.filter((page) => page?.disabled).length === section.pages.length;
        },
    },
    computed: {
        ...mapState(useUserStore, ["user"]),
        ...mapState(useSettingsStore, ["search"]),
        ...mapState(useServerStore, ["is_beta"]),
        settingsSections() {
            const filteredSettingsSearch = this.search ? this.settings.map(this.mapSections).filter(this.filterSections) : this.settings;
            const filteredSettingsRole = filteredSettingsSearch.map(this.mapRoles as any).filter(this.filterSections as any);
            return filteredSettingsRole as any;
        },
    },
    data() {
        return {
            settings: [
                {
                    title: this.__("Main Settings"),
                    description: this.__("General settings for the server"),
                    roles: ["moderator", "user"],
                    pages: [
                        {
                            title: this.__("Media Server"),
                            description: this.__("Configure your media server settings"),
                            icon: "fas fa-server",
                            url: "/admin/settings/media",
                        },
                        {
                            title: this.__("Requests"),
                            description: this.__("Add Jellyseerr, Overseerr or Ombi support"),
                            roles: ["moderator"],
                            icon: "fas fa-link",
                            url: "/admin/settings/requests",
                        },
                        {
                            title: this.__("API keys"),
                            description: this.__("Add API keys for external services"),
                            roles: ["moderator"],
                            icon: "fas fa-key",
                            url: "/admin/settings/apikeys",
                        },
                        {
                            title: this.__("Webhooks"),
                            description: this.__("Add webhooks for external services"),
                            icon: "fas fa-link",
                            url: "/admin/settings/webhooks",
                        },
                        //TODO: hiding unimplemented features
                        // {
                        //     title: this.__("Payments"),
                        //     description: this.__("Configure payment settings"),
                        //     icon: "fas fa-dollar-sign",
                        //     url: "/admin/settings/payments",
                        //     disabled: true,
                        // },
                        // {
                        //     title: this.__("Notifications"),
                        //     description: this.__("Configure notification settings"),
                        //     roles: ["moderator", "user"],
                        //     icon: "fas fa-bell",
                        //     url: "/admin/settings/notifications",
                        //     disabled: true,
                        // },
                        // {
                        //     title: this.__("Discord Bot"),
                        //     description: this.__("Configure Discord bot settings"),
                        //     icon: "fab fa-discord",
                        //     url: "/admin/settings/discord-bot",
                        //     disabled: true,
                        // },
                    ],
                },
                {
                    title: this.__("Account Settings"),
                    description: this.__("Settings for user accounts"),
                    roles: ["moderator", "user"],
                    pages: [
                        {
                            title: this.__("Account"),
                            description: this.__("Configure your account settings"),
                            icon: "fas fa-user-circle",
                            url: "/admin/settings/account",
                        },
                        {
                            title: this.__("Sessions"),
                            description: this.__("View and manage your active sessions"),
                            icon: "fas fa-desktop",
                            url: "/admin/settings/sessions",
                        },
                        {
                            title: this.__("Passkey Authentication"),
                            description: this.__("Configure your passkeys"),
                            icon: "fas fa-shield-alt",
                            url: "/admin/settings/mfa",
                        },
                        // {
                        //     title: this.__("Language"),
                        //     description: this.__("Change your language"),
                        //     icon: "fas fa-language",
                        //     url: "/admin/settings/language",
                        // },
                    ],
                },
                {
                    title: this.__("UI Settings"),
                    description: this.__("Modify the look and feel of the server"),
                    roles: ["moderator"],
                    pages: [
                        {
                            title: this.__("Discord"),
                            description: this.__("Enable Discord page and configure settings"),
                            icon: "fab fa-discord",
                            url: "/admin/settings/discord",
                        },
                        {
                            title: this.__("Onboarding"),
                            description: this.__("Manage onboarding pages"),
                            icon: "fas fa-book",
                            url: "/admin/settings/onboarding",
                        },
                    ],
                },
                {
                    title: this.__("Advanced Settings"),
                    description: this.__("Advanced settings for the server"),
                    pages: [
                        {
                            title: this.__("Logs"),
                            description: this.__("View and download server logs"),
                            icon: "fas fa-file-alt",
                            url: "/admin/settings/logs",
                            modal: true,
                        },
                        {
                            title: this.__("Tasks"),
                            description: this.__("View and manage scheduled tasks"),
                            icon: "fas fa-tasks",
                            url: "/admin/settings/tasks",
                        },
                        //TODO: hiding unimplemented features
                        // {
                        //     title: this.__("Updates"),
                        //     description: this.__("Check for and view updates"),
                        //     icon: "fas fa-sync",
                        //     url: "/admin/settings/updates",
                        //     disabled: true,
                        // },
                        {
                            title: this.__("Bug Reporting"),
                            description: this.__("Manage bug reporting settings"),
                            icon: "fas fa-bug",
                            url: "/admin/settings/sentry",
                        },
                        {
                            title: this.__("Backup"),
                            description: this.__("Create and restore backups"),
                            icon: "fas fa-hdd",
                            url: "/admin/settings/backup",
                        },
                        {
                            title: this.__("About"),
                            description: this.__("View information about the server"),
                            icon: "fas fa-info-circle",
                            url: "/admin/settings/about",
                            modal: true,
                        },
                    ],
                },
            ],
        };
    },
});
</script>
