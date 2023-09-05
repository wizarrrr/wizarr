<template>
    <div class="flex flex-col space-y-4">
        <!-- MFA List -->
        <MFAList />

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
import { useMfaStore } from "@/stores/mfa";

import ListItem from "@/components/ListItem.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

import MFAList from "@/components/MFAList/MFAList.vue";

export default defineComponent({
    name: "MFAView",
    components: {
        ListItem,
        DefaultButton,
        MFAList,
    },
    methods: {
        ...mapActions(useMfaStore, ["createMfa"]),
    },
});
</script>
