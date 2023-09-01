import axios from "@/assets/ts/utils/Axios";
import toasts from "@/assets/ts/utils/Toasts";
import CacheStorage from "@/assets/ts/utils/CacheStorage";

import type { ChangeLog, ChangeLogs } from "@/types/ChangeLog";
import type { AxiosInstance } from "axios";

import { defineStore } from "pinia";
import { buildWebStorage, setupCache, type AxiosCacheInstance } from "axios-cache-interceptor";

const cachedAxios = setupCache(axios as AxiosInstance);

export const useChangeLogStore = defineStore("changeLog", {
    state: () => ({
        cache: {} as any,
        changeLogs: [] as ChangeLogs,
    }),
    actions: {
        fixCachedAxios: (store: any) => {
            cachedAxios.storage = buildWebStorage(new CacheStorage(store));
        },
        async getChangeLogs(per_page: number, page: number) {
            // Fix the cached axios
            this.fixCachedAxios(this);

            // Get the change logs from the API
            const reponse = await cachedAxios.get("https://api.github.com/repos/wizarrrr/wizarr/releases", {
                params: { per_page, page },
                transformRequest: [
                    (data, headers) => {
                        delete headers["X-CSRF-TOKEN"];
                        delete headers["pragma"];
                        delete headers["expires"];
                        delete headers["cache-control"];
                        return data;
                    },
                ],
            });

            // If we didn't get a 200, raise an error
            if (reponse.status !== 200) {
                toasts.error("Could not get Change Logs");
                return;
            }

            // Add the new change logs and update existing ones
            reponse.data.forEach((changeLog: ChangeLog) => {
                const index = this.changeLogs.findIndex((c) => c.id === changeLog.id);
                if (index === -1) {
                    this.changeLogs = [...this.changeLogs, changeLog];
                } else {
                    this.changeLogs = [...this.changeLogs.slice(0, index), changeLog, ...this.changeLogs.slice(index + 1)];
                }
            });
        },
    },
    getters: {
        getReverseChangeLogs: (state) => {
            // Reverse the change logs
            const changeLogs = [...state.changeLogs].reverse();

            // Return the change logs
            return changeLogs;
        },
        getSortedChangeLogs: (state) => {
            // Sort the change logs
            const changeLogs = [...state.changeLogs].sort((a, b) => {
                const dateA = new Date(a.published_at);
                const dateB = new Date(b.published_at);

                return dateB.getTime() - dateA.getTime();
            });

            // Return the change logs
            return changeLogs;
        },
    },
    persist: true,
});
