import { defineStore } from "pinia";
import type { APIUser } from "@/types/api/auth/User";

interface UserStoreState {
    user: Partial<APIUser> | null;
}

export const useUserStore = defineStore("user", {
    state: (): UserStoreState => ({
        user: null,
    }),
    getters: {
        getUser: (state) => {
            return state.user;
        },
    },
    actions: {
        setUser(user: Partial<APIUser>) {
            this.user = user;
        },
    },
    persist: true,
});
