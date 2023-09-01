import { defineStore } from "pinia";

export const useSettingsStore = defineStore("settings", {
    state: () => ({
        search: "" as string,
        header: "search" as "search" | "back",
    }),
});
