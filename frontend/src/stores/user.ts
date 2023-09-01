import { defineStore } from "pinia";
import type { APIUser } from "@/types/User";
import { useJwt } from "@vueuse/integrations/useJwt";
import axios from "@/assets/ts/utils/Axios";

export const useUserStore = defineStore("user", {
    state: () => ({
        user: {} as Partial<APIUser>,
        token: "" as string,
    }),
    getters: {
        isAuthenticated: (state) => {
            // Check if there's a token
            if (!state.token || state.token.length == 0) return false;

            // If there's a token, check if it's expired
            const { header, payload } = useJwt(state.token);
            if (payload.value?.exp && payload.value?.exp < Date.now() / 1000) return false;

            // Otherwise, return true
            return true;
        },
    },
    actions: {
        setUser(user: Partial<APIUser>) {
            this.user = user;
        },
        setToken(token: string) {
            this.token = token;
        },
        logout() {
            this.user = {} as Partial<APIUser>;
            this.token = "";
            axios.get("/api/auth/logout");
        },
    },
    persist: true,
});
