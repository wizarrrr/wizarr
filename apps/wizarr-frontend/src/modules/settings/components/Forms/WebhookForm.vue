<template>
    <FormKit
        v-model="webhookForm"
        @submit="localCreateWebhook"
        type="form"
        :classes="{ input: '!bg-secondary' }"
        :submit-label="__('Create Webhook')"
        :submit-attrs="{ wrapperClass: 'flex justify-end' }"
    >
        <FormKit
            typ="text"
            name="name"
            validation="required|alpha_spaces:latin"
            :label="__('Name')"
            :placeholder="__('My Webhook')"
        />
        <FormKit
            typ="text"
            name="url"
            validation="required|url"
            :label="__('URL')"
            :placeholder="__('https://example.com')"
        />
    </FormKit>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useWebhookStore } from '@/stores/webhooks';
import { mapActions } from 'pinia';

export default defineComponent({
    name: 'WebhookForm',
    data() {
        return {
            webhookForm: {
                name: '',
                url: '',
            },
        };
    },
    methods: {
        localCreateWebhook() {
            this.createWebhook(this.webhookForm);
            this.$emit('close');
        },
        ...mapActions(useWebhookStore, ['createWebhook']),
    },
});
</script>
