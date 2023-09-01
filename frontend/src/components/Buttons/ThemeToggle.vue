<template>
    <div class="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-200 hover:dark:bg-gray-700">
        <button class="text-gray-500 dark:text-gray-400 focus:outline-none text-sm" type="button" @click="toggleTheme">
            <!-- Dark icon -->
            <svg v-if="theme == DARK_VALUE" class="w-5 h-5" fill="currentColor" viewBox="-2 -3 16 21">
                <path d="M 15.229 10.664 C 9.618 13.202 3.364 8.714 3.971 2.585 C 4.057 1.718 4.282 0.793 4.641 0 C -0.971 2.536 -1.576 10.105 3.276 13.581 C 7.215 16.403 13.149 15.267 15.229 10.664 Z"></path>
            </svg>

            <!-- Light icon -->
            <svg v-if="theme == LIGHT_VALUE" class="w-5 h-5" fill="currentColor" viewBox="1 -1 18 21">
                <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" fill-rule="evenodd" clip-rule="evenodd"></path>
            </svg>

            <!-- System icon -->
            <svg v-if="theme == SYSTEM_VALUE" class="w-5 h-5" fill="currentColor" viewBox="0 -2.5 18 21">
                <path d="M 34.41 14.852 C 34.41 19.832 28.985 22.942 24.646 20.453 C 22.634 19.297 21.392 17.161 21.392 14.852 C 21.392 9.872 26.817 6.761 31.155 9.251 C 33.169 10.407 34.41 12.54 34.41 14.852 Z M 19.891 14.852 C 19.891 20.978 26.567 24.807 31.907 21.745 C 34.384 20.325 35.912 17.695 35.912 14.852 C 35.912 8.722 29.237 4.893 23.896 7.958 C 21.418 9.379 19.891 12.006 19.891 14.852 Z" style="opacity: 1" transform="matrix(1, -0.000778, 0.000778, 1, -19.89633, -6.85143)"></path>
                <path d="M 26.678 11.098 L 26.678 15.329 C 26.678 15.576 26.804 15.809 27.013 15.949 L 30.019 17.94 C 30.361 18.17 30.827 18.076 31.06 17.732 C 31.291 17.387 31.196 16.926 30.851 16.696 L 28.182 14.929 L 28.182 11.098 C 28.182 10.684 27.847 10.353 27.429 10.353 C 27.013 10.353 26.678 10.684 26.678 11.098 Z" style="opacity: 1" transform="matrix(1, -0.000778, 0.000778, 1, -19.895831, -6.850628)"></path>
            </svg>
        </button>
    </div>
</template>

<script lang="ts">
import { mapState } from "pinia";
import { mapActions } from "pinia";
import { defineComponent } from "vue";
import { useThemeStore } from "@/stores/theme";
import { LIGHT_VALUE, DARK_VALUE, SYSTEM_VALUE } from "@/assets/ts/utils/DarkMode";

export default defineComponent({
    name: "ThemeToggle",
    data() {
        return {
            LIGHT_VALUE,
            DARK_VALUE,
            SYSTEM_VALUE,
        };
    },
    computed: {
        ...mapState(useThemeStore, ["theme"]),
    },
    methods: {
        ...mapActions(useThemeStore, ["updateTheme", "toggleTheme"]),
    },
});
</script>
