<template>
    <Transition
        name="fade"
        mode="out-in"
        :duration="{ enter: 300, leave: 300 }"
    >
        <template v-if="newAPIKey === null">
            <FormKit
                v-model="apikey"
                @submit="localCreateAPIKey"
                type="form"
                :classes="{ input: '!bg-secondary' }"
                :submit-label="__('Create API Key')"
                :submit-attrs="{ wrapperClass: 'flex justify-end' }"
            >
                <FormKit
                    typ="text"
                    name="name"
                    validation="required|alpha_spaces:latin"
                    :label="__('Name')"
                    :placeholder="__('My API Key')"
                />
            </FormKit>
        </template>
        <template v-else>
            <div class="flex flex-col">
                <div class="text-sm mb-4">
                    {{
                        __(
                            'Please take a copy your API key. You will not be able to see it again, please make sure to store it somewhere safe.',
                        )
                    }}
                </div>
                <FormKit
                    type="text"
                    :value="newAPIKey ?? 'Unknown'"
                    :label="__('API Key')"
                    :disabled="true"
                    :classes="{ input: '!w-full' }"
                />
                <FormKit
                    type="button"
                    @click="copyAPIKey"
                    :classes="{
                        input: '!bg-secondary',
                        wrapper: 'flex justify-end',
                    }"
                >
                    {{ __('Copy') }}
                </FormKit>
            </div>
        </template>
    </Transition>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useAPIKeyStore } from '@/stores/apikeys';
import { mapActions } from 'pinia';
import { useClipboard } from '@vueuse/core';

export default defineComponent({
    name: 'WebhookForm',
    data() {
        return {
            useClipboard: useClipboard(),
            newAPIKey: null as string | null,
            apikey: { name: '' },
        };
    },
    methods: {
        copyAPIKey() {
            this.useClipboard.copy(this.newAPIKey ?? '');
            this.$toast.info(this.__('Copied to clipboard'));
        },
        async localCreateAPIKey() {
            const apikey = await this.createAPIKey(this.apikey);
            this.newAPIKey = apikey?.key ?? null;
        },
        ...mapActions(useAPIKeyStore, ['createAPIKey']),
    },
});
</script>
