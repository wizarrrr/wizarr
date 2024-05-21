import type { User, Users } from '@/types/api/users';
import { defineStore } from 'pinia';

// Interface defining the state structure for the users store
interface UserStoreState {
    users: Users;
}

// Define and export a store for handling user data
export const useUsersStore = defineStore('users', {
    // Initial state setup for the store
    state: (): UserStoreState => ({
        users: [],
    }),
    // Actions that can be called to manipulate the state
    actions: {
        // Asynchronously scans for new users and updates the list if successful
        async scanUsers() {
            const response = await this.$axios.get('/api/users/scan').catch(() => {
                this.$toast.error('Could not scan users'); // Notify user of failure to scan
                return null;
            });

            if (response !== null) {
                await this.getUsers(); // Refresh user list after a successful scan
            }
        },
        // Fetches users from the server and updates the state
        async getUsers() {
            const response = await this.$axios.get<Users, { data: Users }>('/api/users').catch(() => {
                this.$toast.error('Could not get users'); // Notify user of failure to fetch users
                return null;
            });

            if (response !== null) {
                this.updateUsers(response.data); // Update state with new user data
            }
        },
        // Updates user list in the state
        updateUsers(newUsers: Users) {
            const newUserMap = new Map(newUsers.map(user => [user.id, user])); // Map for quick lookup of users
            // Update existing users and add new ones
            const updatedUsers = this.users.map(user => newUserMap.get(user.id) || user);
            newUserMap.forEach((user, id) => {
                if (!this.users.some(u => u.id === id)) {
                    updatedUsers.push(user); // Add new users not already present
                }
            });
            this.users = updatedUsers.filter(user => newUserMap.has(user.id)); // Filter to remove any not returned in the latest fetch
        },
        // Deletes a user from the server and removes from the state
        async deleteUser(id: number) {
            const response = await this.$axios.delete(`/api/users/${id}`, { disableInfoToast: true }).catch(() => {
                this.$toast.error('Could not delete user'); // Notify user of failure to delete
                return null;
            });

            if (response !== null) {
                this.users = this.users.filter(user => user.id !== id); // Remove user from state
            }
        },
    },
    persist: true, // Enable persistence for the store to maintain state across sessions
});
