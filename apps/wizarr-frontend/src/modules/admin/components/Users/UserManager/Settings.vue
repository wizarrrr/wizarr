<template>
    <div class="flex flex-col space-y-4">
        <span
            class="border border-yellow-500 bg-yellow-100 text-yellow-500 px-2 py-1 rounded-md text-xs uppercase font-semibold tracking-wide text-center"
        >
            {{ __('Still under development') }}
        </span>
        <FormKit type="form" :disabled="true">
            <FormKit
                type="text"
                label="Friendly Name"
                name="friendly_name"
                placeholder="John Doe"
                validation="alpha_spaces:latin"
            />
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import type { User } from '@sentry/vue';
import type { Emitter, EventType } from 'mitt';

export default defineComponent({
    name: 'Profile',
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
    mounted() {
        this.eventBus?.on('saveUser', () => {
            console.log('saveUser');
        });
    },
});
</script>
