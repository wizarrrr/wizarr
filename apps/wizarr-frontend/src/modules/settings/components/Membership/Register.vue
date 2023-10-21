<template>
    <div class="flex flex-col">
        <div
            class="flex flex-col space-y-0 px-4 py-3 mb-4 border border-yellow-300 rounded bg-yellow-50 dark:bg-gray-800"
        >
            <div
                class="dark:text-yellow-300 dark:border-yellow-800 text-sm flex flex-col space-y-2 max-w-[400px]"
            >
                <span class="font-medium"
                    >If you meet these requirements, please contact us on
                    Discord to request invitation code:</span
                >
                <ul class="mt-1.5 ml-4 list-disc list-inside">
                    <li>Active Beta tester for Wizarr</li>
                    <li>Donated more than $20 to Wizarr in the last 30 days</li>
                    <li>Are a active monthly paying member to Wizarr</li>
                </ul>
            </div>
        </div>
        <FormKit
            id="register"
            type="form"
            :value="registerData"
            :actions="false"
            @submit="register"
            :classes="{ messages: 'hidden' }"
        >
            <div class="flex flex-col space-y-4">
                <div class="flex flex-col space-y-2">
                    <FormKit
                        name="first_name"
                        label="Your Name"
                        type="text"
                        placeholder="First Name"
                        validation="length:2|*required"
                        autocomplete="given-name"
                        :classes="{
                            outer: '!mb-0',
                            input: 'w-full justify-center',
                        }"
                        :validation-messages="{
                            required: 'First Name is required',
                            length: 'First Name must be at least 2 characters',
                        }"
                    />
                    <FormKit
                        name="last_name"
                        type="text"
                        placeholder="Last Name"
                        validation="length:2|*required"
                        autocomplete="family-name"
                        :classes="{ input: 'w-full justify-center' }"
                        :validation-messages="{
                            required: 'Last Name is required',
                            length: 'Last Name must be at least 2 characters',
                        }"
                    />
                </div>

                <div class="flex flex-col space-y-2">
                    <FormKit
                        name="email"
                        label="Login Details"
                        type="email"
                        placeholder="Email"
                        validation="length:5|*email"
                        :classes="{
                            outer: '!mb-0',
                            input: 'w-full justify-center',
                        }"
                        :validation-messages="{
                            required: 'Email is required',
                            email: 'Email is not valid',
                            length: 'Email must be at least 5 characters',
                        }"
                    />
                    <FormKit
                        name="password"
                        type="password"
                        placeholder="Password"
                        :classes="{ input: 'w-full justify-center' }"
                        validation="length:20|*required"
                        :validation-messages="{
                            required: 'Password is required',
                            length: 'Password must be at least 20 characters',
                        }"
                    />
                </div>

                <!-- Invite Code -->
                <FormKit
                    name="invite_code"
                    type="text"
                    label="Invitation Code"
                    placeholder="Invitation Code"
                    :classes="{ input: 'w-full justify-center' }"
                    validation="length:5|*required"
                    :validation-messages="{
                        required: 'Invitation Code is required',
                        length: 'Invitation Code must be at least 5 characters',
                    }"
                />
            </div>
        </FormKit>
    </div>
</template>

<script lang="ts">
import type { Emitter, EventType } from 'mitt';
import { defineComponent } from 'vue';

export default defineComponent({
    name: 'Register',
    props: {
        eventBus: {
            type: Object as () => Emitter<Record<EventType, unknown>>,
            required: false,
        },
    },
    data() {
        return {
            registerData: {
                email: '',
                password: '',
                invite_code: '',
            },
            membership_api: null as string | null,
        };
    },
    methods: {
        async register(data: typeof this.registerData) {
            const response = await this.$rawAxios
                .post(this.membership_api + '/api/register', data)
                .catch(() => {
                    this.$parent!.$emit('close');
                    this.$toast.error(
                        'Failed to Register to Membership Server',
                    );
                });

            if (!response) return;

            this.$parent!.$emit('close');
            this.$toast.info('Successfully Registered to Membership Server');
        },
    },
    mounted() {
        this.eventBus?.on('register', () => this.$formkit.submit('register'));
        this.membership_api = this.$config('membership_api');
    },
});
</script>
