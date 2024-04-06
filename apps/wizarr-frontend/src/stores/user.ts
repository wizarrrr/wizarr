import type { APIUser as User } from '@/types/api/auth/User';
import { defineStore } from 'pinia';

interface UserStoreState {
    user: Partial<User> | null;
}

export const useUserStore = defineStore('user', {
    state: (): UserStoreState => ({
        user: null,
    }),
    getters: {
        getUser: (state) => {
            return state.user;
        },
    },
    actions: {
        setUser(user: Partial<User>) {
            this.user = user;
        },
        updateUser(user: Partial<User>) {
            this.user = { ...this.user, ...user };
        },
    },
    persist: true,
});
