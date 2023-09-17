<template>
    <button class="text-gray-500 dark:text-gray-400 focus:outline-none text-sm" type="button" @click="visible = !visible">
        <div class="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-200 hover:dark:bg-gray-700">
            <i class="fa-solid fa-md fa-globe"></i>
        </div>
    </button>

    <div class="absolute">
        <LanguageModal :visible="visible" @close="visible = false" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import LanguageModal from "@/components/Modals/LanguageModal.vue";

export default defineComponent({
    name: "LanguageSelector",
    components: {
        LanguageModal,
    },
    data() {
        return {
            visible: false,
        };
    },
});
</script>
