<template>
    <DefaultModal titleString="Set Backend URL" :visible="isVisible" @close="isVisible = false">
        <template #body>
            <span>Test</span>
        </template>
        <template #footer>
            <DefaultButton theme="secondary" @click="triggerSave = !triggerSave">
                {{ __("Save URL") }}
            </DefaultButton>
        </template>
    </DefaultModal>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultModal from "./DefaultModal.vue";
import DefaultButton from "../Buttons/DefaultButton.vue";

export default defineComponent({
    name: "ScanLibrariesModal",
    components: {
        DefaultModal,
        DefaultButton,
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
