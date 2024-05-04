import { defineStore } from 'pinia';

export const useLibrariesStore = defineStore('libraries', {
    state: () => ({
        libraries: [] as Array<{ id: string; name: string; created: Date }>,
    }),
    actions: {
        async getLibraries() {
            try {
                const response = await this.$axios.get('/api/libraries');
                if (!response?.data) {
                    throw new Error('Invalid response data');
                }
                this.libraries = response.data.map(({ id, name, created }: { id: string; name: string; created: string }) => ({
                    id,
                    name,
                    created: new Date(created)
                }));
            } catch (error) {
                this.$toast.error('Could not get libraries');
            }
        },

        async saveLibraries(libraries: Array<{ id: string; name: string; selected: boolean }>) {
            try {
                const selectedLibraries = libraries.filter(lib => lib.selected).map(lib => lib.id);
                const formData = new FormData();
                formData.append('libraries', JSON.stringify(selectedLibraries));
                const response = await this.$axios.post('/api/libraries', formData, { disableInfoToast: true });
                if (!response?.data?.message) {
                    throw new Error('No success message in response');
                }
                this.$toast.info('Successfully saved libraries');
            } catch (error) {
                this.$toast.error('Could not save libraries');
            }
        },

        async scanLibraries() {
            try {
                const [libResponse, scanResponse] = await Promise.all([
                    this.$axios.get('/api/libraries'),
                    this.$axios.get('/api/scan-libraries')
                ]);

                if (!libResponse?.data || !scanResponse?.data?.libraries) {
                    throw new Error('Invalid response data');
                }

                this.libraries = libResponse.data.map(({ id, name, created }: { id: string; name: string; created: string }) => ({
                    id,
                    name,
                    created: new Date(created)
                }));

                const allLibrariesMap = new Map(this.libraries.map(lib => [lib.id, lib.name]));
                const newLibraries = Object.entries(scanResponse.data.libraries).map(([name, id]) => ({
                    id,
                    name,
                    selected: allLibrariesMap.has(id)
                }));

                return newLibraries;
            } catch (error) {
                this.$toast.error('Could not get libraries');
            }
        },
    },
    persist: true,
});
