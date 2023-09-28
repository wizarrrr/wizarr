<template>
    <form class="space-y-4 md:space-y-6" @submit.prevent="$emit('passwordLogin')">
        <div class="flex justify-center flex-col space-y-4">
            <h1 class="text-gray-900 dark:text-white text-2xl font-semibold">Login with your account</h1>
        </div>

        <DefaultInput v-model:value="usernameValue" label="Username" name="username" placeholder="Username" required autocomplete="username webauthn" :autofocus="!passwordAutofocus" :restrictions="{ disable_spaces: true }" />
        <DefaultInput v-model:value="passwordValue" label="Password" name="password" placeholder="Password" required autocomplete="current-password" :autofocus="passwordAutofocus" type="password" />

        <div class="space-y-2">
            <DefaultButton type="submit" theme="primary" :options="{ button: { button_class: 'w-full' } }">
                {{ __("Login") }}
            </DefaultButton>
            <div v-if="!hideMFA" class="flex justify-center items-center">
                <button type="button" @click="$emit('mfaLogin')" class="text-secondary text-sm font-medium">
                    {{ __("Login with Passkey") }}
                </button>
            </div>
        </div>
    </form>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultInput from "@/components/Inputs/DefaultInput.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

export default defineComponent({
    name: "PasswordForm",
    components: {
        DefaultInput,
        DefaultButton,
    },
    props: {
        hideMFA: {
            type: Boolean,
            default: false,
        },
        username: {
            type: String,
            required: true,
        },
        password: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            usernameValue: this.username,
            passwordValue: this.password,
        };
    },
    computed: {
        passwordAutofocus(): boolean {
            return this.hideMFA || this.usernameValue.length > 0;
        },
    },
    watch: {
        usernameValue: {
            immediate: true,
            handler(value: string) {
                this.$emit("update:username", value);
            },
        },
        passwordValue: {
            immediate: true,
            handler(value: string) {
                this.$emit("update:password", value);
            },
        },
    },
});
</script>
