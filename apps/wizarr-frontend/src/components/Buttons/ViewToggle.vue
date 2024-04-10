<template>
    <VTooltip>
        <button class="text-gray-500 dark:text-gray-400 focus:outline-none text-sm" type="button" @click="toggleBoxView">
            <div class="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-200 hover:dark:bg-gray-700">
                <!-- Box Icon -->
                <i v-if="boxView" class="fas fa-box"></i>

                <!-- List Icon -->
                <i v-else class="fas fa-list"></i>
            </div>
        </button>

        <template #popper>
            <span>{{ __("Toggle View") }}</span>
        </template>
    </VTooltip>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapWritableState } from "pinia";
import { useThemeStore } from "@/stores/theme";

export default defineComponent({
    name: "ViewToggle",
    computed: {
        ...mapWritableState(useThemeStore, ["boxView"]),
    },
    methods: {
        toggleBoxView() {
            this.boxView = !this.boxView;
        },
    },
});
</script>
