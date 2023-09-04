<template>
    <DefaultModal titleString="Select Libraries" :visible="isVisible" @close="isVisible = false">
        <template #body>
            <ScanLibrariesAsync :triggerSave="triggerSave" @close="isVisible = false" />
        </template>
        <template #footer>
            <DefaultButton theme="secondary" @click="triggerSave = !triggerSave">
                {{ __("Select Libraries") }}
            </DefaultButton>
        </template>
    </DefaultModal>
</template>

<script lang="ts">
import { defineComponent, defineAsyncComponent } from "vue";

import DefaultModal from "./DefaultModal.vue";
import DefaultButton from "../Buttons/DefaultButton.vue";
import DefaultLoading from "../Loading/DefaultLoading.vue";
import DefaultError from "../Errors/DefaultError.vue";

const ScanLibrariesAsync = defineAsyncComponent({
    loader: () => import("../ScanLibraries/ScanLibraries.vue"),
    loadingComponent: DefaultLoading,
    errorComponent: DefaultError("Failed to load", "Could not load the libraries."),
});

export default defineComponent({
    name: "ScanLibrariesModal",
    components: {
        DefaultModal,
        DefaultButton,
        ScanLibrariesAsync,
    },
    props: {
        visible: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            isVisible: this.visible,
            triggerSave: false,
        };
    },
    watch: {
        visible: {
            handler() {
                this.isVisible = this.visible;
            },
            immediate: true,
        },
        isVisible: {
            handler() {
                this.$emit("update:visible", this.isVisible);
            },
            immediate: true,
        },
    },
});
</script>
