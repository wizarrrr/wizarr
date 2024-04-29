<template>
    <div class="flex flex-col space-y-4">
        <div class="flex flex-col justify-center items-start space-y-2">
            <span class="text-md font-semibold text-gray-900 dark:text-white">{{
                title
            }}</span>
            <span class="text-sm text-gray-900 dark:text-white">{{
                message
            }}</span>
        </div>
        <FormKit
            @click="continueToLogin"
            type="button"
            :classes="{ input: 'w-full justify-center' }"
        >
            {{ __('Continue to Login') }}
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
    name: 'Error',
    props: {
        title: {
            type: String,
            required: true,
        },
        message: {
            type: String,
            required: true,
        },
    },
    methods: {
        async continueToLogin() {
            // Warn user that an error occured and there account may not of been created
            await this.$modal.confirmModal(
                this.__('Account Error'),
                this.__(
                    'An error occured while creating your account, your account may of not of been created, if you face issue attempting to login, please contact an admin.',
                ),
                {
                    confirmButtonText: this.__('Okay'),
                    disableCancelButton: true,
                },
            );

            // Redirect to help page
            this.$router.push({ name: 'help' });
        },
    },
});
</script>
