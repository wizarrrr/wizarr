<template>
    <div class="mx-[-1.5rem] mt-[-1.5rem]">
        <Tabbed :tabs="tabs" class="px-7 pt-7 pb-2" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import type { User } from '@/types/api/users';
import type { Emitter, EventType } from 'mitt';

import Tabbed from '@/modules/core/components/Tabbed.vue';

export default defineComponent({
    name: 'UserManager',
    components: {
        Tabbed,
    },
    props: {
        user: {
            type: Object as () => User,
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
                    name: 'User',
                    icon: 'fa-user',
                    props: {
                        user: this.user,
                        eventBus: this.eventBus,
                    },
                    component: () => import('./User.vue'),
                },
                {
                    name: 'Invitation',
                    icon: 'fa-envelope',
                    disabled: true,
                    hidden: this.env.NODE_ENV === 'production',
                    props: {
                        user: this.user,
                        eventBus: this.eventBus,
                    },
                    component: () => import('./Invitation.vue'),
                },
                {
                    name: 'Schedule',
                    icon: 'fa-calendar',
                    disabled: true,
                    hidden: this.env.NODE_ENV === 'production',
                    props: {
                        user: this.user,
                        eventBus: this.eventBus,
                    },
                    component: () => import('./AccessSchedule.vue'),
                },
                {
                    name: 'Permissions',
                    icon: 'fa-shield',
                    disabled: true,
                    hidden: this.env.NODE_ENV === 'production',
                    props: {
                        user: this.user,
                        eventBus: this.eventBus,
                    },
                    component: () => import('./Permissions.vue'),
                },
                {
                    name: 'Settings',
                    icon: 'fa-cog',
                    disabled: true,
                    hidden: this.env.NODE_ENV === 'production',
                    props: {
                        user: this.user,
                        eventBus: this.eventBus,
                    },
                    component: () => import('./Settings.vue'),
                },
            ],
            disabled: {
                delete: false,
            },
        };
    },
});
</script>
