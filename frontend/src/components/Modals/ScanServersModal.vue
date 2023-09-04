<template>
    <DefaultModal titleString="Select Servers" :visible="isVisible" @close="isVisible = false">
        <template #body>
            <ScanServersAsync :tryAgain="tryAgain" v-model:subnet="selectedSubnet" @close="isVisible = false" />
        </template>
        <template #footer>
            <DefaultButton theme="danger" :disabled="selectedSubnet == 'disabled'" @click="tryAgain = !tryAgain">
                {{ __("Try Again") }}
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

const ScanServersAsync = defineAsyncComponent({
    loader: () => import("../ScanServers/ScanServers.vue"),
    loadingComponent: DefaultLoading,
    errorComponent: DefaultError("Failed to load", "Could not load the servers."),
});

export default defineComponent({
    name: "ScanLibrariesModal",
    components: {
        DefaultModal,
        DefaultButton,
        ScanServersAsync,
    },
    props: {
        visible: {
            type: Boolean,
            default: true,
        },
    },
    data() {
        return {
            isVisible: this.visible,
            tryAgain: false,
            selectedSubnet: null,
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
