import type { Server, ServerSettings } from "@/assets/ts/api/ServerData";
import { defineStore } from "pinia";

export const useServerStore = defineStore("server", {
    state: () => ({
        settings: {} as ServerSettings,
        version: "" as string,
        update_available: false as boolean,
        debug: false as boolean,
        setup_required: false as boolean,
    }),
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
