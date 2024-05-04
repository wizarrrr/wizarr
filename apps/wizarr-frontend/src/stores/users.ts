import type { User, Users } from '@/types/api/users';
import { defineStore } from 'pinia';

interface UserStoreState {
    users: Users;
}

export const useUsersStore = defineStore('users', {
    state: (): UserStoreState => ({
        users: [],
    }),
    actions: {
        async scanUsers() {
            const response = await this.$axios.get('/api/users/scan').catch(() => {
                this.$toast.error('Could not scan users');
                return null;
            });

            if (response !== null) {
                await this.getUsers();
            }
        },
        async getUsers() {
            const response = await this.$axios.get<Users, { data: Users }>('/api/users').catch(() => {
                this.$toast.error('Could not get users');
                return null;
            });

            if (response !== null) {
                this.updateUsers(response.data);
            }
        },
        updateUsers(newUsers: Users) {
            // Build a map of new users for quick lookup
            const newUserMap = new Map(newUsers.map(user => [user.id, user]));
            // Filter and update existing users
            const updatedUsers = this.users.map(user => newUserMap.get(user.id) || user);
            // Add new users who aren't already in the store
            newUserMap.forEach((user, id) => {
                if (!this.users.some(u => u.id === id)) {
                    updatedUsers.push(user);
                }
            });
            // Set the new users array to the state
            this.users = updatedUsers.filter(user => newUserMap.has(user.id));
        },
        async deleteUser(id: number) {
            const response = await this.$axios.delete(`/api/users/${id}`, { disableInfoToast: true }).catch(() => {
                this.$toast.error('Could not delete user');
                return null;
            });

            if (response !== null) {
                this.users = this.users.filter(user => user.id !== id);
            }
        },
    },
    getters: {},
    persist: true,
});
