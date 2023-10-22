<template>
    <div class="block w-full">
        <FormKit
            type="form"
            @submit="join"
            :submit-label="__('Join')"
            :submit-attrs="{ inputClass: 'w-full justify-center mt-2' }"
        >
            <FormKit
                type="text"
                v-model="code"
                :label="__('Invite Code')"
                :value="code"
                placeholder="XMFGEJI"
            />
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
    name: 'JoinForm',
    data() {
        return {
            code: String(this.$route.params.invite || ''),
        };
    },
    methods: {
        async join() {
            // Check if the code is inputted
            if (!this.code || this.code.length !== 6) {
                this.$toast.info(this.__('Please enter an invite code'));
                return;
            }

            // Show the please wait
            this.$emit('pleaseWait', true);

            // Check if the code is valid
            const response = await this.$axios
                .get(`/api/invitations/${this.code}/verify`, {
                    disableInfoToast: true,
                    disableErrorToast: true,
                })
                .catch((err) => {
                    this.$emit('pleaseWait', false);
                    this.$toast.error(
                        this.__('Invalid invitation code, please try again'),
                    );
                });

            // Check if the code is valid
            if (!response) return;

            // If the route is /join then change to /j/:code
            if (this.$route.path === '/join') {
                this.$router.replace(`/j/${this.code}`);
            }

            // Go to the next step
            this.$emit('pleaseWait', false);
            this.$emit('nextStep');
        },
    },
});
</script>
