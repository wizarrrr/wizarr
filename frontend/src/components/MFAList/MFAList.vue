<template>
    <Draggable v-if="mfas" v-model="mfas" tag="ul" group="mfa" ghost-class="moving-card" :animation="200" item-key="id">
        <template #item="{ element }">
            <li class="mb-2">
                <MFAItem :mfa="element" />
            </li>
        </template>
    </Draggable>
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
