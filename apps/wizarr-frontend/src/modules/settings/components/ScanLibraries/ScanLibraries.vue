<template>
    <div class="flex flex-col space-y-2">
        <template v-if="libraries.length > 0" v-for="library in libraries">
            <ScanLibrariesItem
                :libraryID="library.id"
                :libraryName="library.name"
                :selected="library.selected"
                @update:selected="updateSelected"
            />
        </template>
        <template v-else>
            <div class="flex flex-col space-y-2">
                <div
                    class="flex flex-col justify-center items-center space-x-2"
                >
                    <i
                        class="fas fa-spinner fa-spin text-2xl text-gray-900 dark:text-white"
                    ></i>
                    <span class="text-gray-900 dark:text-white"
                        >Please wait...</span
                    >
                </div>
            </div>
        </template>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions } from 'pinia';
import { useLibrariesStore } from '@/stores/libraries';

import type { Emitter, EventType } from 'mitt';

import ScanLibrariesItem from './ScanLibrariesItem.vue';

declare interface LibraryItem {
    id: string;
    name: string;
    selected: boolean;
}

export default defineComponent({
    name: 'ScanLibraries',
    components: {
        ScanLibrariesItem,
    },
    props: {
        eventBus: {
            type: Object as () => Emitter<Record<EventType, unknown>>,
            required: true,
        },
    },
    data() {
        return {
            libraries: [] as LibraryItem[],
        };
    },
    methods: {
        async localScanLibraries() {
            const newLibraries = await this.scanLibraries();

            if (!newLibraries) {
                this.$toast.error('Could not scan libraries');
                return;
            }

            this.libraries = newLibraries;
        },
        async localSaveLibraries() {
            if (this.libraries === null) {
                this.$toast.error('Could not save libraries');
                return;
            }

            await this.saveLibraries(this.libraries);
            this.$emit('close');
        },
        updateSelected({
            libraryID,
            selected,
        }: {
            libraryID: string;
            selected: boolean;
        }) {
            if (this.libraries === null) {
                return;
            }

            const index = this.libraries.findIndex(
                (library) => library.id === libraryID,
            );
            this.libraries[index].selected = selected;
        },
        ...mapActions(useLibrariesStore, ['saveLibraries', 'scanLibraries']),
    },
    mounted() {
        this.localScanLibraries();
        this.eventBus.on('selectLibraries', this.localSaveLibraries);
    },
});
</script>
