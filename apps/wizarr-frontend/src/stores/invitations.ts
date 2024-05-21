// Import the types for invitations and the Pinia library function for creating a store
import type { Invitation, Invitations } from '@/types/api/invitations';
import { defineStore } from 'pinia';

// Define the shape of the state in this store
interface InvitationStoreState {
    invitations: Invitations;
}

// Define and export a store named 'invitations' using the Pinia library
export const useInvitationStore = defineStore('invitations', {
    // Define the initial state of the store
    state: (): InvitationStoreState => ({
        invitations: [],
    }),
    // Define actions that can mutate the state
    actions: {
        // Asynchronously fetches invitations from the server and updates the state
        async getInvitations() {
            const response = await this.$axios
                .get<Invitations, { data: Invitations }>('/api/invitations')
                .catch(() => {
                    this.$toast.error('Could not get invitations');
                    return null;
                });

            if (response !== null) {
                this.updateInvitations(response.data);
            }
        },
        // Updates the current invitations state with new data
        updateInvitations(newInvitations: Invitations) {
            const newInvitationMap = new Map(newInvitations.map(invite => [invite.id, invite]));
            const updatedInvitations = this.invitations.map(invite => newInvitationMap.get(invite.id) || invite);
            newInvitationMap.forEach((invite, id) => {
                if (!this.invitations.some(i => i.id === id)) {
                    updatedInvitations.push(invite);
                }
            });
            this.invitations = updatedInvitations.filter(invite => newInvitationMap.has(invite.id));
        },
        // Creates a new invitation on the server and updates the local state if successful
        async createInvitation(invitation: FormData | Partial<Invitation>) {
            const response = await this.$axios
                .post('/api/invitations', invitation, {
                    disableErrorToast: true,
                })
                .catch((err) => {
                    this.$toast.error('Could not create invitation');
                    console.error(err);
                    return null;
                });

            if (response !== null) {
                this.invitations.push(response.data as Invitation);
                return response.data as Invitation;
            }
        },
        // Deletes an invitation from the server and removes it from the local state if successful
        async deleteInvitation(id: number) {
            const response = await this.$axios
                .delete(`/api/invitations/${id}`, { disableInfoToast: true })
                .catch((err) => {
                    this.$toast.error('Could not delete invitation');
                    console.error(err);
                    return null;
                });

            if (response !== null) {
                this.invitations = this.invitations.filter(invitation => invitation.id !== id);
            }
        },
    },
    // Persist the state of the store to local storage or another persistence layer
    persist: true,
});
