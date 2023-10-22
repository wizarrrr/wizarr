<template>
    <Draggable
        :disabled="isDisabled"
        v-if="invitations && invitations.length > 0"
        v-model="invitations"
        tag="ul"
        group="invites"
        ghost-class="moving-card"
        :animation="200"
        item-key="id"
    >
        <template #item="{ element }">
            <li class="mb-2">
                <InvitationItem :invite="element" />
            </li>
        </template>
    </Draggable>
    <div v-else class="flex flex-col justify-center items-center space-y-1">
        <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
        <span class="text-gray-400">{{ __('No Invitations found') }}</span>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useInvitationStore } from '@/stores/invitations';
import { mapActions, mapWritableState } from 'pinia';
import { usePointer } from '@vueuse/core';

import Draggable from 'vuedraggable';
import InvitationItem from './InvitationItem.vue';

export default defineComponent({
    name: 'InviteList',
    components: {
        Draggable,
        InvitationItem,
    },
    data() {
        return {
            pointer: usePointer(),
        };
    },
    computed: {
        isDisabled() {
            return this.pointer.pointerType !== 'mouse' || false;
        },
        ...mapWritableState(useInvitationStore, ['invitations']),
    },
    methods: {
        ...mapActions(useInvitationStore, ['getInvitations']),
    },
    async created() {
        await this.getInvitations();
    },
});
</script>
