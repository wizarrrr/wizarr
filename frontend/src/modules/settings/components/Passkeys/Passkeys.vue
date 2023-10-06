<template>
    <Draggable v-if="mfas && mfas.length > 0" v-model="mfas" tag="ul" group="mfa" ghost-class="moving-card" :animation="200" item-key="id">
        <template #item="{ element }">
            <li class="mb-2">
                <PasskeysItem :mfa="element" />
            </li>
        </template>
    </Draggable>
    <div v-else class="flex flex-col justify-center items-center space-y-1">
        <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
        <span class="text-gray-400">{{ __("No Passkeys found") }}</span>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { usePasskeysStore } from "@/stores/passkeys";
import { mapActions, mapWritableState } from "pinia";

import Draggable from "vuedraggable";
import PasskeysItem from "./PasskeysItem.vue";

export default defineComponent({
    name: "PasskeyList",
    components: {
        Draggable,
        PasskeysItem,
    },
    computed: {
        ...mapWritableState(usePasskeysStore, ["mfas"]),
    },
    methods: {
        ...mapActions(usePasskeysStore, ["getMfas"]),
    },
    async created() {
        await this.getMfas();
    },
});
</script>
