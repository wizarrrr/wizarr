<template>
    <div class="mx-[-1.5rem] mt-[-1.5rem]">
        <Tabbed :tabs="tabs" class="px-7 pt-7 pb-2" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import type { Invitation } from '@/types/api/invitations';
import type { Emitter, EventType } from 'mitt';

import Tabbed from '@/modules/core/components/Tabbed.vue';

export default defineComponent({
    name: 'UserManager',
    components: {
        Tabbed,
    },
    props: {
        invitation: {
            type: Object as () => Invitation,
            required: true,
        },
        eventBus: {
            type: Object as () => Emitter<Record<EventType, unknown>>,
            required: false,
        },
    },
    data() {
        return {
            tabs: [
                {
                    name: 'Invitation',
                    icon: 'fa-envelope',
                    props: {
                        invitation: this.invitation,
                        eventBus: this.eventBus,
                    },
                    component: () => import('./Invitation.vue'),
                },
            ],
        };
    },
});
</script>
