<template>
    <div class="flex flex-col space-y-4">
        <!-- MFA List -->
        <PasskeysList />

        <!-- Add MFA -->
        <div class="flex flex-row justify-end items-center">
            <DefaultButton @click="createMfa()" theme="secondary" icon="fas fa-plus" :options="{ icon: { icon_position: 'left' } }">
                {{ __("Add Passkey") }}
            </DefaultButton>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { mapActions } from "pinia";
import { usePasskeysStore } from "@/stores/passkeys";

import DefaultButton from "@/components/Buttons/DefaultButton.vue";
import PasskeysList from "../components/Passkeys/Passkeys.vue";

export default defineComponent({
    name: "Passkeys",
    components: {
        DefaultButton,
        PasskeysList,
    },
    methods: {
        ...mapActions(usePasskeysStore, ["createMfa"]),
    },
});
</script>
