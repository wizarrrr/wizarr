import axios from "@/ts/utils/axios";

import { errorToast } from "@/ts/utils/toasts";
import { defineStore } from "pinia";

export const useLibrariesStore = defineStore("libraries", {
    state: () => ({
        libraries: [] as Array<{ id: string; name: string; created: Date }>,
    }),
    actions: {
        async getLibraries() {
            let libraries: Array<{ id: string; name: string; created: Date }> = [];
            const response = await axios()
                .get("/api/libraries")
                .catch((error) => {
                    errorToast(error);
                });

            if (response?.data) {
                libraries = response.data.map((library: { id: string; name: string; created: string }) => {
                    return {
                        id: library.id,
                        name: library.name,
                        created: new Date(library.created),
                    };
                });
            }

            this.libraries = libraries;
            return libraries;
        },
    },
    persist: true,
});
