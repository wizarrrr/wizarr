import type { Invitation, Invitations } from '@/types/api/invitations';

import { defineStore } from 'pinia';

interface InvitationStoreState {
    invitations: any[];
}

export const useInvitationStore = defineStore('invitations', {
    state: (): InvitationStoreState => ({
        invitations: [] as Invitations,
    }),
    actions: {
        async getInvitations() {
            // Get invites from API
            const invitations = await this.$axios
                .get<Invitations, { data: Invitations }>('/api/invitations')
                .catch(() => {
                    this.$toast.error('Could not get invitations');
                    return null;
                });

            // If the invites are null, return
            if (invitations === null) return;

            // Update the invites that are already in the store
            this.invitations.forEach((invite, index) => {
                const new_invitation = invitations.data.find(
                    (new_invitation: Invitation) =>
                        new_invitation.id === invite.id,
                );
                if (new_invitation) this.invitations[index] = new_invitation;
            });

            // Add the new invites to the store if they don't exist
            invitations.data.forEach((invitation: Invitation) => {
                if (
                    !this.invitations.find(
                        (old_invitation) => old_invitation.id === invitation.id,
                    )
                )
                    this.invitations.push(invitation);
            });

            // Remove the invites that were not in the response
            this.invitations.forEach((invitation, index) => {
                if (
                    !invitations.data.find(
                        (new_invitation: Invitation) =>
                            new_invitation.id === invitation.id,
                    )
                )
                    this.invitations.splice(index, 1);
            });

            // Return the invites
            return invitations.data;
        },
        async createInvitation(invitation: FormData | Partial<Invitation>) {
            // Create the invite
            const response = await this.$axios
                .post('/api/invitations', invitation, {
                    disableErrorToast: true,
                })
                .catch((err) => {
                    this.$toast.error('Could not create invitation');
                    console.error(err);
                    return null;
                });

            // If the response is null, return
            if (response === null) return;

            // Add the invite to the store
            this.invitations.push(response.data as Invitation);

            // Return the invite
            return response.data as Invitation;
        },
        async deleteInvitation(id: number) {
            // Delete the invite from the API
            const response = await this.$axios
                .delete(`/api/invitations/${id}`, { disableInfoToast: true })
                .catch((err) => {
                    this.$toast.error('Could not delete invitation');
                    console.error(err);
                    return null;
                });

            // If the response is null, return
            if (response === null) return;

            // Remove the invite from the store
            const index = this.invitations.findIndex(
                (invitation: Invitation) => invitation.id === id,
            );
            if (index !== -1) this.invitations.splice(index, 1);
        },
    },
    persist: true,
});
