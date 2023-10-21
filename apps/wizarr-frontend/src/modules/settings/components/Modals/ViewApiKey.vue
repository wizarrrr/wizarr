<template>
    <FormKit
        type="text"
        :value="apiKey"
        :readonly="true"
        :help="__('Click the key to copy to clipboard!')"
        outer-class="!mb-0"
        @click="copyToClipboard"
    />
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useClipboard } from '@vueuse/core';

export default defineComponent({
    name: 'ViewAPIKey',
    props: {
        apiKey: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            clipboard: useClipboard({
                legacy: true,
            }),
        };
    },
    methods: {
        copyToClipboard() {
            if (this.clipboard.isSupported) {
                this.clipboard.copy(this.apiKey);
                this.$toast.info(this.__('Copied to clipboard'));
            }
        },
    },
});
</script>
