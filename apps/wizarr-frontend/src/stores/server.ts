import type { Server, ServerSettings } from "@/types/api/server";

import type { Requests } from "@/types/api/request";
import { defineStore } from "pinia";

export const useServerStore = defineStore("server", {
    state: () => ({
        settings: {} as ServerSettings,
        requests: [] as Requests,
        version: "" as string,
        update_available: false as boolean,
        debug: false as boolean,
        setup_required: false as boolean,
        is_beta: false as boolean,
        latest_version: "" as string,
        latest_beta_version: "" as string,
    }),
    getters: {
        isBugReporting(state) {
            if (state.settings.bug_reporting === undefined) return true;
            return state.settings.bug_reporting === "true";
        }
    },
    actions: {
        setServerData(server_data: Partial<Server> | undefined) {
            if (server_data !== undefined) {
                Object.keys(server_data).forEach((key: string) => {
                    if ((this as any)[key] !== undefined) (this as any)[key] = (server_data as { [key: string]: any })[key];
                });
            }
        },
    },
    persist: true,
});
