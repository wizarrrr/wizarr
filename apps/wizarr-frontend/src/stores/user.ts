import type { Membership } from '@/types/api/membership';
import type { APIUser as User } from '@/types/api/auth/User';
import { defineStore } from 'pinia';

interface UserStoreState {
    user: Partial<User> | null;
    membership: Membership | null;
}

export const useUserStore = defineStore('user', {
    state: (): UserStoreState => ({
        user: null,
        membership: null,
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
        setMembership(membership: Membership | null) {
            this.membership = membership;
        },
        updateMembership(membership: Partial<Membership>) {
            this.membership = {
                ...this.membership,
                ...membership,
            } as Membership;
        },
    },
    persist: true,
});
