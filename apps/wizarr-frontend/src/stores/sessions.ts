import type { Session, Sessions } from '@/types/api/sessions';
import { defineStore } from 'pinia';

interface SessionsStoreState {
    sessions: Sessions;
}

export const useSessionsStore = defineStore('sessions', {
    state: (): SessionsStoreState => ({
        sessions: [],
    }),
    actions: {
        async getSessions() {
            // Get the sessions from the API
            const sessions = await this.$axios
                .get<Sessions, { data: Sessions }>('/api/sessions')
                .catch((err) => {
                    this.$toast.error('Could not get sessions');
                    return null;
                });

            // If the sessions are null, return
            if (sessions === null) return;

            // Update the sessions that are already in the store
            this.sessions.forEach((session, index) => {
                const new_session = sessions.data.find(
                    (new_session: Session) => new_session.id === session.id,
                );
                if (new_session) this.sessions[index] = new_session;
            });

            // Add the new sessions to the store if they don't exist
            sessions.data.forEach((session: Session) => {
                if (
                    !this.sessions.find(
                        (old_session) => old_session.id === session.id,
                    )
                )
                    this.sessions.push(session);
            });

            // Remove the sessions that were not in the response
            this.sessions.forEach((session, index) => {
                if (
                    !sessions.data.find(
                        (new_session: Session) => new_session.id === session.id,
                    )
                )
                    this.sessions.splice(index, 1);
            });
        },
        async deleteSession(id: number) {
            // Delete the session from the API
            const response = await this.$axios
                .delete(`/api/sessions/${id}`)
                .catch((err) => {
                    this.$toast.error('Could not delete session');
                    console.error(err);
                    return null;
                });

            // If the response is null, return
            if (response === null) return;

            // Remove the session from the store
            const index = this.sessions.findIndex(
                (session: Session) => session.id === id,
            );
            if (index !== -1) this.sessions.splice(index, 1);
        },
    },
    persist: true,
});
