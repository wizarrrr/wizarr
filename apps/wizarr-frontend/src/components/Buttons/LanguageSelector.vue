<template>
    <VTooltip>
        <button class="text-gray-500 dark:text-gray-400 focus:outline-none text-sm" type="button" @click="createModal">
            <div :class="iconClasses" class="flex items-center justify-center rounded hover:bg-gray-200 hover:dark:bg-gray-700">
                <i class="fa-solid fa-md fa-globe"></i>
            </div>
        </button>

        <template #popper>
            <span>{{ __("Language") }}</span>
        </template>
    </VTooltip>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import LanguageModal from "@/components/Modals/LanguageModal.vue";

export default defineComponent({
    name: "LanguageSelector",
    components: {
        LanguageModal,
    },
    props: {
        iconClasses: {
            type: String,
            default: "w-6 h-6",
        },
    },
    computed: {
        iconClasses(): string {
            return this.iconClasses;
        },
    },
    methods: {
        createModal() {
            this.$modal.openModal(LanguageModal, {
                title: this.__("Select Language"),
                disableFooter: true,
            });
        },
    },
});
</script>
