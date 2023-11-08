<template>
    <div :class="bordered">
        <div class="flex flex-col space-y-6">
            <div class="xterm"></div>
            <div class="flex flex-row justify-end" v-if="isModal">
                <FormKit type="button" @click="openLarge">
                    {{ __("Open Window") }}
                </FormKit>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { Terminal } from "xterm";
import { mapState } from "pinia";
import { defineComponent } from "vue";
import { FitAddon } from "xterm-addon-fit";
import { useThemeStore } from "@/stores/theme";
import { useDebounceFn } from "@vueuse/core";
import { useServerStore } from "@/stores/server";

import type { ITheme, ITerminalOptions } from "xterm";
import type { Socket } from "socket.io-client";

import { useAuthStore } from "@/stores/auth";

export default defineComponent({
    name: "LogsView",
    props: {
        eventBus: {
            type: Object,
            required: false,
        },
    },
    data() {
        return {
            socket: null as Socket | null,
            terminal: new Terminal(),
            fitAddon: new FitAddon(),
            options: {
                convertEol: true,
                fontFamily: `'Fira Mono', monospace`,
                fontSize: 15,
            } as ITerminalOptions,
            theme: {
                dark: {
                    foreground: "#ffffff",
                    background: "transparent",
                },
                light: {
                    foreground: "#000000",
                    background: "transparent",
                },
            } as Record<string, ITheme>,
            isModal: false,
        };
    },
    computed: {
        bordered() {
            return !this.boxView && !this.isModal ? "border border-gray-200 dark:border-gray-700 rounded-md p-6" : "";
        },
        ...mapState(useServerStore, ["settings"]),
        ...mapState(useThemeStore, ["boxView"]),
        ...mapState(useThemeStore, ["currentTheme"]),
        ...mapState(useAuthStore, ["token"]),
    },
    methods: {
        async onData() {
            this.terminal.scrollToBottom();
        },
        async onResize() {
            this.fitAddon.fit();
        },
        openLarge() {
            this.$router.push("/admin/settings/logs");
        },
    },
    async mounted() {
        // Initialize the terminal
        this.terminal.options = this.options;
        this.terminal.loadAddon(this.fitAddon);
        this.terminal.open(this.$el.querySelector(".xterm") as HTMLElement);
        this.fitAddon.fit();

        // Initialize the callbacks
        this.terminal.onData(useDebounceFn(this.onData.bind(this), 1000));
        window.addEventListener("resize", this.onResize);

        // Initialize previous logs
        const response = await this.$axios.get("/api/logging/text").catch(() => {
            return;
        });

        this.terminal.write(response?.data ?? "");

        // Initialize the socket
        this.socket = this.$io("/logging", {
            extraHeaders: {
                Authorization: `Bearer ${this.token}`,
            },
        });

        // Initialize the socket callbacks
        this.socket.on("connect", () => {
            this.terminal.writeln("Connected to the logging server\n");
        });

        this.socket.on("disconnect", () => {
            this.terminal.writeln("Disconnected from the logging server\n");
        });

        this.socket.on("log", (data: string) => {
            this.terminal.write(data);
        });

        if (this.eventBus) {
            this.isModal = true;
        }
    },
    unmounted() {
        this.socket?.disconnect();
        window.removeEventListener("resize", this.onResize);
    },
    watch: {
        currentTheme: {
            handler() {
                this.terminal.options.theme = this.theme[this.currentTheme];
            },
            immediate: true,
        },
    },
});
</script>
