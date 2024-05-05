import type { Session, Sessions } from '@/types/api/sessions';
import { defineStore } from 'pinia';

// Interface defining the state structure for the sessions store
interface SessionsStoreState {
    sessions: Sessions;
}

// Define and export a store for handling session data
export const useSessionsStore = defineStore('sessions', {
    // Initial state setup for the store
    state: (): SessionsStoreState => ({
        sessions: [],
    }),
    // Actions that can be called to manipulate the state
    actions: {
        // Asynchronously fetches session data from the server and updates the store
        async getSessions() {
            try {
                const response = await this.$axios.get<Sessions>('/api/sessions');
                if (!response.data) throw new Error('No data received');

                // Create a map of new sessions for quick lookup
                const newSessionsMap = new Map<number, Session>(response.data.map((session: Session) => [session.id, session]));

                // Update existing sessions and add new ones
                this.sessions = this.sessions.reduce((updatedSessions: Session[], session) => {
                    if (newSessionsMap.has(session.id)) {
                        const newSession = newSessionsMap.get(session.id);
                        if (newSession) {
                            updatedSessions.push(newSession);
                            newSessionsMap.delete(session.id); // Remove updated session from the map to avoid duplication
                        }
                    } else {
                        updatedSessions.push(session); // Keep sessions that weren't updated
                    }
                    return updatedSessions;
                }, []);
            } catch (error) {
                this.$toast.error('Could not get sessions'); // Notify the user of failure to fetch sessions
                console.error(error);
            }
        },

        // Asynchronously deletes a session from the server and removes it from the store
        async deleteSession(id: number) {
            try {
                await this.$axios.delete(`/api/sessions/${id}`);
                const index = this.sessions.findIndex(session => session.id === id);
                if (index !== -1) {
                    this.sessions.splice(index, 1); // Remove the session from the store if found
                }
            } catch (error) {
                this.$toast.error('Could not delete session'); // Notify the user of failure to delete session
                console.error(error);
            }
        },
    },
    persist: true, // Enable persistence for the store to maintain state across sessions
});
