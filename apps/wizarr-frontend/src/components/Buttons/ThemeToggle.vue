<template>
    <VTooltip>
        <button class="text-gray-500 dark:text-gray-400 focus:outline-none text-sm" type="button" @click="toggleTheme">
            <div :class="iconClasses" class="flex items-center justify-center rounded hover:bg-gray-200 hover:dark:bg-gray-700">
                <i v-if="theme == DARKMODE" class="fa-solid fa-md fa-cloud-moon"></i>
                <i v-if="theme == LIGHTMODE" class="fa-solid fa-md fa-sun"></i>
                <i v-if="theme == SYSTEMMODE" class="fa-solid fa-md fa-desktop"></i>
            </div>
        </button>

        <template #popper>
            <span>{{ __("Change Theme") }}</span>
        </template>
    </VTooltip>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapState, mapActions } from "pinia";
import { useThemeStore } from "@/stores/theme";
import { LIGHTMODE, DARKMODE, SYSTEMMODE } from "@/ts/utils/darkMode";

export default defineComponent({
    name: "ThemeToggle",
    data() {
        return {
            LIGHTMODE,
            DARKMODE,
            SYSTEMMODE,
        };
    },
    props: {
        iconClasses: {
            type: String,
            default: "w-6 h-6",
        },
    },
    computed: {
        ...mapState(useThemeStore, ["theme"]),
        iconClasses(): string {
            return this.iconClasses;
        },
    },
    methods: {
        ...mapActions(useThemeStore, ["updateTheme", "toggleTheme"]),
    },
});
</script>
