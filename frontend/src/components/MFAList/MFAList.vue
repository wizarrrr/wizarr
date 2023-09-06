<template>
    <Draggable v-if="mfas && mfas.length > 0" v-model="mfas" tag="ul" group="mfa" ghost-class="moving-card" :animation="200" item-key="id">
        <template #item="{ element }">
            <li class="mb-2">
                <MFAItem :mfa="element" />
            </li>
        </template>
    </Draggable>
    <div v-else class="flex flex-col justify-center items-center">
        <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
        <span class="text-gray-400">{{ __("No Passkeys found") }}</span>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useMfaStore } from "@/stores/mfa";
import { mapActions, mapWritableState } from "pinia";

import Draggable from "vuedraggable";
import MFAItem from "./MFAItem.vue";

export default defineComponent({
    name: "TasksView",
    components: {
        Draggable,
        MFAItem,
    },
    computed: {
        ...mapWritableState(useMfaStore, ["mfas"]),
    },
    methods: {
        ...mapActions(useMfaStore, ["getMfas"]),
    },
    async created() {
        await this.getMfas();
    },
});
</script>
