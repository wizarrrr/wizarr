<template>
    <div>
        <h1 class="text-xl text-center font-bold leading-tight tracking-tight text-gray-900 md:text-2xl dark:text-white">
            {{ __("You're Done") }}
        </h1>
        <p class="text-base text-center text-gray-500 dark:text-gray-400 md:text-lg">
            {{ __("You have successfully completed the setup process.") }}
        </p>
        <div class="flex justify-center mt-6">
            <DefaultButton @click="completeSetup">
                {{ __("Go to Login") }}
            </DefaultButton>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import DefaultButton from "@/components/Buttons/DefaultButton.vue";

export default defineComponent({
    name: "CompleteView",
    components: {
        DefaultButton,
    },
    methods: {
        async completeSetup() {
            await this.$axios.get("/api/setup/exit");
            this.$router.push("/login");
        },
    },
});
</script>
