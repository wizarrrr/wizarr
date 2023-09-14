<template>
    <div>
        <div class="flex justify-center items-center flex-col mt-12 mb-3 space-y-6">
            <WizarrLogo rounded class="w-[150px] h-[150px]" />
            <h1 class="text-2xl font-semibold text-center text-gray-900 dark:text-white">{{ __("Type in your invite code to %{server_name} server!", { server_name: settings.server_name }) }}</h1>
        </div>
        <section>
            <div class="flex flex-col items-center justify-center md:container py-8 mx-auto">
                <div class="w-full md:w-1/2 lg:w-1/3 bg-white rounded shadow dark:border dark:bg-gray-800 dark:border-gray-700 overflow-hidden">
                    <div class="relative">
                        <div class="text-gray-900 dark:text-white" :class="{ 'space-y-4': !noHeader }">
                            <h1 class="px-6 pt-6 sm:px-8 sm:pt-8 relative text-xl font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white" v-if="!noHeader">
                                <Transition name="fade" mode="out-in" :duration="{ enter: 200, leave: 200 }">
                                    <div v-if="currentView == 1">
                                        {{ __("Join the %{server_type} Server", { server_type: $filter("firstLetterUppercase", settings.server_type) }) }}
                                    </div>
                                    <div v-else-if="currentView == 2">
                                        {{ __("Setup your account") }}
                                    </div>
                                    <div v-else-if="currentView == 3" :key="activeStepTitle">
                                        {{ activeStepTitle }}
                                    </div>
                                    <div v-else-if="currentView == 4">
                                        {{ __("Your account has been created!") }}
                                    </div>
                                </Transition>
                            </h1>
                            <div class="block w-full" :class="{ 'pt-6 sm:pt-8': noHeader }">
                                <Carousel :views="views" :currentView="currentView" @current="(current) => (currentView = current)" />
                            </div>
                        </div>
                        <Transition name="fade" mode="out-in" :duration="{ enter: 200, leave: 200 }">
                            <div class="z-20 bg-white dark:bg-gray-800 absolute top-0 right-0 bottom-0 left-0 flex justify-center items-center flex-col space-y-1" v-if="pleaseWait">
                                <i class="fa-solid fa-spinner fa-spin text-4xl text-center text-gray-900 dark:text-white"></i>
                                <p class="text-center font-semibold text-gray-900 dark:text-white">{{ __("Please wait...") }}</p>
                            </div>
                        </Transition>
                    </div>
                </div>
            </div>
        </section>
    </div>
</template>

<script lang="ts">
import { mapState } from "pinia";
import { defineComponent } from "vue";
import { useServerStore } from "@/stores/server";
import { Collapse } from "vue-collapsed";

import Carousel from "@/components/Carousel.vue";
import WizarrLogo from "@/components/WizarrLogo.vue";

import JoinForm from "@/components/Forms/JoinForm.vue";
import CreateAccountView from "./CreateAccountView.vue";
import JoinStepperView from "./StepperView.vue";
import JoinCompleteView from "./CompleteView.vue";
import JoinErrorView from "./ErrorView.vue";

import mitt from "mitt";

import type { Socket } from "socket.io-client";
import type { ServerToClientEvents, ClientToServerEvents } from "@/plugins/socket";
import type { JellyfinForm } from "./JellyfinViews/JellyfinSetupView.vue";

type EmitterRecords = {
    "*": any;
    join: string;
    plexCreateAccount: string;
    jellyfinCreateAccount: JellyfinForm;
    pleaseWait: boolean;
    activeStepTitle: string;
    step: number;
};

const eventBus = mitt<EmitterRecords>();

export default defineComponent({
    name: "JoinView",
    components: {
        WizarrLogo,
        Carousel,
        JoinForm,
        Collapse,
    },
    data() {
        return {
            socket: null as Socket<ServerToClientEvents, ClientToServerEvents> | null,
            eventBus: eventBus,
            pleaseWait: true,
            activeStepTitle: "Please wait...",
            currentView: 1,
            views: [
                {
                    name: "join",
                    view: JoinForm,
                    props: {
                        eventBus: eventBus,
                        code: this.$route.params.invite as string,
                    },
                },
                {
                    name: "create",
                    view: CreateAccountView,
                    props: {
                        eventBus: eventBus,
                    },
                },
                {
                    name: "stepper",
                    view: JoinStepperView,
                    props: {
                        eventBus: eventBus,
                    },
                },
                {
                    name: "success",
                    view: JoinCompleteView,
                },
                {
                    name: "error",
                    view: JoinErrorView,
                    props: {
                        title: this.__("Uh oh!"),
                        message: this.__("Something went wrong while trying to join the server. Please try again later."),
                    },
                },
            ],
        };
    },
    computed: {
        noHeader() {
            return this.isView(["error"]);
        },
        ...mapState(useServerStore, ["settings"]),
    },
    methods: {
        isView(name: string | string[]) {
            return Array.isArray(name) ? name.includes(this.views[this.currentView - 1].name) : this.views[this.currentView - 1].name == name;
        },
        async showError(title: string, message: string) {
            // Hide the please wait screen
            this.pleaseWait = false;

            // Go to the error screen
            this.currentView = this.views.findIndex((view) => view.name == "error") + 1;
            this.views[this.currentView - 1].props = {
                title: title,
                message: message,
            };
        },
        async connected() {
            // Hide the please wait screen
            this.pleaseWait = false;

            // Check for a socket id
            if (this.socket?.id == undefined) {
                this.showError(this.__("Uh oh!"), this.__("Could not connect to the server."));
            }
        },
        async join(value: EmitterRecords["join"]) {
            // Show the please wait screen
            this.pleaseWait = true;

            // Check if the code is valid
            await this.$axios.get(`/api/invitations/${value}/verify`, { disableInfoToast: true }).catch((err) => {
                this.pleaseWait = false;
                this.currentView = this.views.findIndex((view) => view.name == "error");
                this.views[this.currentView].props = {
                    title: this.__("Invalid Invite!"),
                    message: err.response?.data?.message ?? this.__("Could not verify the invite code."),
                };
            });

            // Hide the please wait screen and go to the next view
            this.pleaseWait = false;
            this.currentView++;
        },
        async plexCreateAccount(value: EmitterRecords["plexCreateAccount"]) {
            // Show the next screen
            this.currentView++;

            // Create the form data
            const formData = new FormData();
            formData.append("token", value);
            formData.append("code", this.$route.params.invite as string);
            formData.append("socket_id", this.socket?.id as string);

            // Make API request to create the account
            const response = await this.$axios.post("/api/plex", formData).catch((err) => {
                this.showError(this.__("Uh oh!"), err.response?.data?.message ?? this.__("Could not create the account."));
            });

            // Check that response contains a room
            if (response?.data?.room == undefined) {
                this.showError(this.__("Uh oh!"), this.__("Could not create the account."));
            }
        },
        async jellyfinCreateAccount(value: EmitterRecords["jellyfinCreateAccount"]) {
            // Show the next screen
            this.currentView++;

            // Create the form data
            const formData = new FormData();
            formData.append("username", value.username);
            formData.append("email", value.email);
            formData.append("password", value.password);
            formData.append("code", this.$route.params.invite as string);
            formData.append("socket_id", this.socket?.id as string);

            // Make API request to create the account
            const response = await this.$axios.post("/api/jellyfin", formData).catch((err) => {
                this.showError(this.__("Uh oh!"), err.response?.data?.message ?? this.__("Could not create the account."));
            });

            // Check that response contains a room
            if (response?.data?.room == undefined) {
                this.showError(this.__("Uh oh!"), this.__("Could not create the account."));
            }
        },
    },
    async mounted() {
        // Initialize the socket connection
        this.socket = this.$io("/" + this.settings.server_type);
        this.socket.on("connect", () => this.connected());
        this.socket.on("connect_error", () => this.showError(this.__("Uh oh!"), this.__("Could not connect to the server.")));
        this.socket.on("error", (message) => this.showError(this.__("Uh oh!"), message));
        this.socket.on("error", this.$toast.error);
        this.socket.on("message", this.$toast.info);
        this.socket.on("step", (step: number) => this.eventBus.emit("step", step));
        this.socket.on("done", () => setTimeout(() => this.currentView++, 1000));

        // Initialize the event bus
        this.eventBus.on("join", this.join);
        this.eventBus.on("plexCreateAccount", this.plexCreateAccount);
        this.eventBus.on("jellyfinCreateAccount", this.jellyfinCreateAccount);
        this.eventBus.on("pleaseWait", (pleaseWait) => (this.pleaseWait = pleaseWait));
        this.eventBus.on("activeStepTitle", (title) => (this.activeStepTitle = title));

        // join=true automatically triggers the join event
        if (this.$route.query.join == "true") {
            this.join(this.$route.params.invite as string);
        }
    },
    async beforeUnmount() {
        // Disconnect the socket
        this.socket?.disconnect();

        // Remove the event bus listeners
        this.eventBus.off("*");
    },
});
</script>
