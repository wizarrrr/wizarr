import { defineStore } from 'pinia';

// Define and export a Pinia store named 'libraries'
export const useLibrariesStore = defineStore('libraries', {
    // Define the state with initial structure for libraries
    state: () => ({
        libraries: [] as Array<{ id: string; name: string; created: Date }>,
    }),
    // Define actions that can mutate the state
    actions: {
        // Asynchronously fetches libraries from the server and updates the state
        async getLibraries() {
            try {
                const response = await this.$axios.get('/api/libraries');
                if (!response?.data) {
                    throw new Error('Invalid response data'); // Throws an error if the data is not as expected
                }
                this.libraries = response.data.map(({ id, name, created }: { id: string; name: string; created: string }) => ({
                    id,
                    name,
                    created: new Date(created) // Convert 'created' string to Date object
                }));
            } catch (error) {
                this.$toast.error('Could not get libraries'); // Show error notification if the request fails
            }
        },

        // Saves selected libraries back to the server
        async saveLibraries(libraries: Array<{ id: string; name: string; selected: boolean }>) {
            try {
                const selectedLibraries = libraries.filter(lib => lib.selected).map(lib => lib.id);
                const formData = new FormData();
                formData.append('libraries', JSON.stringify(selectedLibraries));
                const response = await this.$axios.post('/api/libraries', formData, { disableInfoToast: true });
                if (!response?.data?.message) {
                    throw new Error('No success message in response'); // Check for a success message in the response
                }
                this.$toast.info('Successfully saved libraries'); // Notification for successful operation
            } catch (error) {
                this.$toast.error('Could not save libraries'); // Show error notification if the operation fails
            }
        },

        // Asynchronously fetches and synchronizes library data with a scan operation
        async scanLibraries() {
            try {
                const [libResponse, scanResponse] = await Promise.all([
                    this.$axios.get('/api/libraries'), // Get current libraries
                    this.$axios.get('/api/scan-libraries') // Perform a scanning operation
                ]);

                if (!libResponse?.data || !scanResponse?.data?.libraries) {
                    throw new Error('Invalid response data'); // Validate responses
                }

                this.libraries = libResponse.data.map(({ id, name, created }: { id: string; name: string; created: string }) => ({
                    id,
                    name,
                    created: new Date(created) // Update libraries state
                }));

                const allLibrariesMap = new Map(this.libraries.map(lib => [lib.id, lib.name]));
                const newLibraries = Object.entries(scanResponse.data.libraries).map(([name, id]) => ({
                    id,
                    name,
                    selected: allLibrariesMap.has(id) // Mark if already present
                }));

                return newLibraries; // Return new libraries for potential further processing
            } catch (error) {
                this.$toast.error('Could not get libraries'); // Error handling
            }
        },
    },
    persist: true, // Enable state persistence across sessions
});
