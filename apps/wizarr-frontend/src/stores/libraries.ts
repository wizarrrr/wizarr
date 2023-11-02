import { defineStore } from 'pinia';

export const useLibrariesStore = defineStore('libraries', {
    state: () => ({
        libraries: [] as Array<{ id: string; name: string; created: Date }>,
    }),
    actions: {
        async getLibraries() {
            // Get the libraries from the API
            const response = await this.$axios.get('/api/libraries');

            // Check if the response is valid
            if (!response?.data) {
                this.$toast.error('Could not get libraries');
                return;
            }

            // Map the libraries to the correct format
            this.libraries = response.data.map(
                (library: { id: string; name: string; created: string }) => {
                    return {
                        id: library.id,
                        name: library.name,
                        created: new Date(library.created),
                    };
                },
            );
        },
        async saveLibraries(
            libraries: Array<{ id: string; name: string; selected: boolean }>,
        ) {
            const formData = new FormData();
            const newLibraries: string[] = [];

            libraries.forEach((library) => {
                if (library.selected) {
                    newLibraries.push(library.id);
                }
            });

            formData.append('libraries', JSON.stringify(newLibraries));

            const response = await this.$axios
                .post('/api/libraries', formData, { disableInfoToast: true })
                .catch(() => {
                    return;
                });

            if (!response?.data?.message) {
                this.$toast.error('Could not save libraries');
                return;
            }

            this.$toast.info('Successfully saved libraries');
        },
        async scanLibraries() {
            // Get the libraries from the API
            const libResponse = await this.$axios.get('/api/libraries');

            // Check if the response is valid
            if (!libResponse?.data) {
                this.$toast.error('Could not get libraries');
                return;
            }

            // Map the libraries to the correct format
            const allLibraries = libResponse.data.map(
                (library: { id: string; name: string; created: string }) => {
                    return {
                        id: library.id,
                        name: library.name,
                        created: new Date(library.created),
                    };
                },
            ) as Array<{ id: string; name: string; created: Date }>;

            // Update the libraries in the store
            this.libraries = allLibraries;

            // Get the libraries from the media server
            const scanResponse = await this.$axios.get('/api/scan-libraries');

            // Check if the response is valid
            if (!scanResponse?.data?.libraries) {
                this.$toast.error('Could not get libraries');
                return;
            }

            // Map the libraries to the correct format
            const libraries: [string, string][] = Object.entries(
                scanResponse.data.libraries,
            );
            const newLibraries: Array<{
                id: string;
                name: string;
                selected: boolean;
            }> = [];

            // Check if the library is selected
            for (const [name, id] of libraries) {
                const selected =
                    allLibraries.find((library) => library.id === id) !==
                    undefined;
                newLibraries.push({ id: id, name: name, selected: selected });
            }

            return newLibraries;
        },
    },
    persist: true,
});
