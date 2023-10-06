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
        updateUser(user: Partial<APIUser>) {
            // Create a new form data object
            const formData = new FormData();
            if (user.display_name) formData.append("display_name", user.display_name);
            if (user.username) formData.append("username", user.username);
            if (user.email) formData.append("email", user.email);

            // Update the user in the database
            this.$axios.put("/api/accounts", formData).then((response) => {
                this.user = response.data;
            });

            // Update the user in the store
            this.user = { ...this.user, ...user };
        },
    },
    persist: true,
});
