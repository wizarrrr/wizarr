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
            // Trigger the scan through the API
            const response = await this.$axios
                .get('/api/users/scan')
                .catch(() => {
                    this.$toast.error('Could not scan users');
                    return null;
                });

            // If the response is null, return
            if (response === null) return;

            // Trigger the get users function
            await this.getUsers();
        },
        async getUsers() {
            // Get the users from the API
            const users = await this.$axios
                .get<Users, { data: Users }>('/api/users')
                .catch(() => {
                    this.$toast.error('Could not get users');
                    return null;
                });

            // If the users are null, return
            if (users === null) return;

            // Update the users that are already in the store
            this.users.forEach((user, index) => {
                const new_user = users.data.find(
                    (new_user: User) => new_user.id === user.id,
                );
                if (new_user) this.users[index] = new_user;
            });

            // Add the new users to the store if they don't exist
            users.data.forEach((user: User) => {
                if (!this.users.find((old_user) => old_user.id === user.id))
                    this.users.push(user);
            });

            // Remove the users that were not in the response
            this.users.forEach((user, index) => {
                if (
                    !users.data.find(
                        (new_user: User) => new_user.id === user.id,
                    )
                )
                    this.users.splice(index, 1);
            });

            // Return the users
            return users.data;
        },
        async deleteUser(id: number) {
            // Delete the user from the API
            const response = await this.$axios
                .delete(`/api/users/${id}`, { disableInfoToast: true })
                .catch(() => {
                    this.$toast.error('Could not delete user');
                    return null;
                });

            // If the response is null, return
            if (response === null) return;

            // Remove the user from the store
            const index = this.users.findIndex((user: User) => user.id === id);
            if (index !== -1) this.users.splice(index, 1);
        },
    },
    getters: {},
    persist: true,
});
