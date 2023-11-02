<template>
    <form class="space-y-4 md:space-y-6" @submit.prevent>
        <div class="flex justify-center flex-col space-y-4">
            <h1 class="text-gray-900 dark:text-white text-2xl font-semibold">
                {{ __('Login with your account') }}
            </h1>
        </div>

        <DefaultInput
            v-model:value.trim="usernameValue"
            name="username"
            placeholder="Username"
            required
            autocomplete="username webauthn"
            autofocus
            :restrictions="{ disable_spaces: true }"
        />
        <DefaultButton
            type="submit"
            theme="secondary"
            :options="{
                text: { text_class: 'text-white' },
                button: { button_class: 'w-full text-sm' },
            }"
        >
            {{ __('Continue') }}
        </DefaultButton>
    </form>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import DefaultButton from '@/components/Buttons/DefaultButton.vue';
import DefaultInput from '@/components/Inputs/DefaultInput.vue';

export default defineComponent({
    name: 'UsernameForm',
    components: {
        DefaultButton,
        DefaultInput,
    },
    props: {
        username: {
            type: String,
            default: '',
        },
    },
    data() {
        return {
            usernameValue: this.username,
        };
    },
    watch: {
        usernameValue: {
            immediate: true,
            handler(value: string) {
                this.$emit('update:username', value);
            },
        },
    },
});
</script>
