import { defineStore } from 'pinia';
import { useJwt } from '@vueuse/integrations/useJwt';

export type AuthStoreState = {
    token: string | null;
    refresh_token: string | null;
};

export const useAuthStore = defineStore('auth', {
    state: (): AuthStoreState => ({
        token: null,
        refresh_token: null,
    }),
    getters: {
        getAccessToken: (state) => {
            return state.token;
        },
        getRefreshToken: (state) => {
            return state.refresh_token;
        },
    },
    actions: {
        isAuthenticated() {
            return !this.isAccessTokenExpired();
        },
        setAccessToken(token: string) {
            this.token = token;
        },
        setRefreshToken(token: string) {
            this.refresh_token = token;
        },
        removeAccessToken() {
            this.token = null;
        },
        removeRefreshToken() {
            this.refresh_token = null;
        },
        isAccessTokenExpired() {
            if (!this.token) return true;
            const { payload } = useJwt(this.token);
            if (payload.value?.exp && payload.value?.exp < Date.now() / 1000)
                return true;
            return false;
        },
        isRefreshTokenExpired() {
            if (!this.refresh_token) return true;
            const { payload } = useJwt(this.refresh_token);
            if (payload.value?.exp && payload.value?.exp < Date.now() / 1000)
                return true;
            return false;
        },
    },
    persist: true,
});
