<template>
    <div class="flex flex-col space-y-4">
        <p>
            {{
                __(
                    'Please login to your Plex account to help us connect you to our server.',
                )
            }}
        </p>
        <FormKit
            @click="login()"
            type="button"
            :classes="{ input: 'w-full justify-center' }"
        >
            {{ __('Login to Plex') }}
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import type { Emitter, EventType } from 'mitt';

import PlexAuth from '@/ts/utils/plexAuth';

export default defineComponent({
    name: 'PlexSetupView',
    data() {
        return {
            auth: new PlexAuth(),
        };
    },
    props: {
        eventBus: {
            type: Object as () => Emitter<Record<EventType, unknown>>,
            required: false,
        },
    },
    methods: {
        async login() {
            // Confirm with user that Plex may warn them about unverified app usage
            const confirm = await this.$modal.confirmModal(
                this.__('Plex Warning'),
                this.__(
                    'Wizarr is an unverified app. This means that Plex may warn you about using it. Do you wish to continue?',
                ),
                { confirmButtonText: this.__('Okay') },
            );

            // If user doesn't confirm, don't continue
            if (!confirm) return;

            // Login to Plex
            this.$emit('pleaseWait', true);
            const token = await this.auth.login();
            this.$emit('pleaseWait', false);

            // If we have a token, emit it to the parent component
            if (token) this.eventBus?.emit('plexCreateAccount', token);
            else this.$toast.error('Failed to login to Plex');
        },
    },
});
</script>
