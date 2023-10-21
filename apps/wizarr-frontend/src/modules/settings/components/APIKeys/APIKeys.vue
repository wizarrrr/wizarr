<template>
    <Draggable
        v-if="apikeys && apikeys.length > 0"
        v-model="apikeys"
        tag="ul"
        group="apikeys"
        ghost-class="moving-card"
        :animation="200"
        item-key="id"
    >
        <template #item="{ element }">
            <li class="mb-2">
                <APIKeyItem :apikey="element" />
            </li>
        </template>
    </Draggable>
    <div v-else class="flex flex-col justify-center items-center space-y-1">
        <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
        <span class="text-gray-400">{{ __('No API Keys found') }}</span>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useAPIKeyStore } from '@/stores/apikeys';
import { mapActions, mapWritableState } from 'pinia';

import Draggable from 'vuedraggable';
import APIKeyItem from './APIKeysItem.vue';

export default defineComponent({
    name: 'APIKeyList',
    components: {
        Draggable,
        APIKeyItem,
    },
    computed: {
        ...mapWritableState(useAPIKeyStore, ['apikeys']),
    },
    methods: {
        ...mapActions(useAPIKeyStore, ['getAPIKeys']),
    },
    async created() {
        await this.getAPIKeys();
    },
});
</script>
