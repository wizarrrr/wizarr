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
            try {
                const response = await this.$axios.get<Sessions>('/api/sessions');
                if (!response.data) throw new Error('No data received');

                const newSessionsMap = new Map<number, Session>(response.data.map((session: Session) => [session.id, session]));

                // Update existing sessions and add new ones
                this.sessions = this.sessions.reduce((updatedSessions: Session[], session) => {
                    if (newSessionsMap.has(session.id)) {
                        const newSession = newSessionsMap.get(session.id);
                        if (newSession) {
                            updatedSessions.push(newSession);
                            newSessionsMap.delete(session.id);
                        }
                    } else {
                        updatedSessions.push(session);
                    }
                    return updatedSessions;
                }, []);
            } catch (error) {
                this.$toast.error('Could not get sessions');
                console.error(error);
            }
        },

        async deleteSession(id: number) {
            try {
                await this.$axios.delete(`/api/sessions/${id}`);
                const index = this.sessions.findIndex(session => session.id === id);
                if (index !== -1) this.sessions.splice(index, 1);
            } catch (error) {
                this.$toast.error('Could not delete session');
                console.error(error);
            }
        },
    },
    persist: true,
});
