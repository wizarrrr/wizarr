<template>
    <div
        :class="{ [classesString]: true, [background]: true }"
        @click="toggleLibrary"
    >
        <label :for="libraryID" class="w-full py-2">
            <div class="w-full text-lg font-semibold">{{ libraryName }}</div>
        </label>
        <i
            v-if="itemSelected"
            class="fas fa-check text-green-500 dark:text-green-400"
        ></i>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
    name: 'ScanLibrariesItem',
    props: {
        libraryID: {
            type: String,
            required: true,
        },
        libraryName: {
            type: String,
            required: true,
        },
        selected: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    data() {
        return {
            itemSelected: this.selected,
            classes: [
                'dark:hover:bg-gray-600 hover:bg-gray-100', // Hover background color
                'dark:hover:text-gray-200 hover:text-gray-500', // Hover text color
                'dark:text-gray-300 text-gray-600', // Text color
                'dark:hover:border-gray-600 hover:border-gray-100', // Hover border color
                'dark:border-gray-600 border-gray-100', // Border color
                'inline-flex items-center justify-between', // Flexbox
                'w-full px-4', // Size and padding
                'border-2 rounded cursor-pointer', // Border and cursor
            ],
            selectedBackground: 'dark:bg-gray-600 bg-gray-100',
            unselectedBackground: 'dark:bg-gray-700 bg-gray-50',
        };
    },
    computed: {
        classesString(): string {
            return this.classes.join(' ');
        },
        background(): string {
            if (this.itemSelected) return this.selectedBackground;
            else return this.unselectedBackground;
        },
    },
    methods: {
        toggleLibrary() {
            this.$emit('update:selected', {
                libraryID: this.libraryID,
                selected: !this.itemSelected,
            });

            this.itemSelected = !this.itemSelected;
        },
    },
    watch: {
        selected: {
            immediate: true,
            handler() {
                this.itemSelected = this.selected;
            },
        },
    },
});
</script>
