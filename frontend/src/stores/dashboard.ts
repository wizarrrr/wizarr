import { defineStore } from "pinia";
import { nanoid } from "nanoid";

import type { WidgetOptions } from "@/types/local/WidgetOptions";

interface DashboardStoreState {
    dashboard: WidgetOptions[];
}

export const useDashboardStore = defineStore("dashboard", {
    state: (): DashboardStoreState => ({
        dashboard: [
            {
                id: nanoid(),
                type: "InvitesTotal",
                grid: { w: 2, h: 2 },
            },
            {
                id: nanoid(),
                type: "UsersTotal",
                grid: { w: 2, h: 2 },
            },
        ],
    }),
    actions: {
        updateWidget(widget: WidgetOptions) {
            const index = this.dashboard.findIndex((w) => w.id === widget.id);
            this.dashboard[index] = widget;
        },
        deleteWidget(id: string) {
            const index = this.dashboard.findIndex((w) => w.id === id);
            this.dashboard.splice(index, 1);
        },
    },
    persist: true,
});
