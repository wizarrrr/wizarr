<template>
    <div class="flex flex-col space-y-2">
        <template v-for="library in selectedLibraries" v-if="selectedLibraries !== null">
            <ScanLibrariesItem :libraryID="library.id" :libraryName="library.name" :selected="library.selected" @update:selected="updateSelected" />
        </template>
        <template v-else>
            <div class="flex flex-col space-y-2">
                <div class="flex flex-col justify-center items-center space-x-2">
                    <i class="fas fa-spinner fa-spin text-2xl text-gray-900 dark:text-white"></i>
                    <span class="text-gray-900 dark:text-white">Loading libraries...</span>
                </div>
            </div>
        </template>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapActions, mapState } from "pinia";
import { useLibrariesStore } from "@/stores/libraries";

import ScanLibrariesItem from "./ScanLibrariesItem.vue";

export default defineComponent({
    name: "ScanLibraries",
    components: {
        ScanLibrariesItem,
    },
    props: {
        triggerSave: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    data() {
        return {
            selectedLibraries: null as Array<{ id: string; name: string; selected: boolean }> | null,
        };
    },
    computed: {
        ...mapState(useLibrariesStore, ["libraries"]),
    },
    methods: {
        ...mapActions(useLibrariesStore, ["getLibraries"]),
        async scanLibraries() {
            const response = await this.$axios.get("/api/scan-libraries").catch(() => {
                return;
            });

            if (!response?.data?.libraries) {
                this.$toast.error("Could not get libraries");
                return;
            }

            const libraries: [string, string][] = Object.entries(response.data.libraries);
            const newLibraries: Array<{ id: string; name: string; selected: boolean }> = [];

            for (const [name, id] of libraries) {
                const selected = this.libraries.find((library) => library.id === id) !== undefined;
                console.log(this.libraries);
                newLibraries.push({ id: id, name: name, selected: selected });
            }

            this.selectedLibraries = newLibraries;
        },
        async saveLibraries() {
            const formData = new FormData();
            const newLibraries: string[] = [];

            if (this.selectedLibraries === null) {
                this.$toast.error("Could not save libraries");
                return;
            }

            this.selectedLibraries.forEach((library) => {
                if (library.selected) {
                    newLibraries.push(library.id);
                }
            });

            formData.append("libraries", JSON.stringify(newLibraries));

            const response = await this.$axios.post("/api/libraries", formData, { disableInfoToast: true }).catch(() => {
                return;
            });

            if (!response?.data?.message) {
                this.$toast.error("Could not save libraries");
                return;
            }

            this.$toast.info("Successfully saved libraries");
            this.$emit("close");
        },
        updateSelected({ libraryID, selected }: { libraryID: string; selected: boolean }) {
            if (this.selectedLibraries === null) {
                return;
            }

            const index = this.selectedLibraries.findIndex((library) => library.id === libraryID);
            this.selectedLibraries[index].selected = selected;
        },
    },
    watch: {
        triggerSave: {
            handler() {
                this.saveLibraries();
            },
            immediate: false,
        },
    },
    async mounted() {
        await this.getLibraries();
        await this.scanLibraries();
    },
});
</script>
