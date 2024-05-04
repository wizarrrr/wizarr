import type { Invitation, Invitations } from '@/types/api/invitations';
import { defineStore } from 'pinia';

interface InvitationStoreState {
    invitations: Invitations;
}

export const useInvitationStore = defineStore('invitations', {
    state: (): InvitationStoreState => ({
        invitations: [],
    }),
    actions: {
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
        updateInvitations(newInvitations: Invitations) {
            // Build a map of new invitations for quick lookup
            const newInvitationMap = new Map(newInvitations.map(invite => [invite.id, invite]));
            // Filter and update existing invitations
            const updatedInvitations = this.invitations.map(invite => newInvitationMap.get(invite.id) || invite);
            // Add new invitations who aren't already in the store
            newInvitationMap.forEach((invite, id) => {
                if (!this.invitations.some(i => i.id === id)) {
                    updatedInvitations.push(invite);
                }
            });
            // Set the new invitations array to the state
            this.invitations = updatedInvitations.filter(invite => newInvitationMap.has(invite.id));
        },
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
    persist: true,
});
