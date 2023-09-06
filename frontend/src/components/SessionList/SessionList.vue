<template>
    <Draggable v-model="sessions" tag="ul" group="sessions" ghost-class="moving-card" :animation="200" item-key="id">
        <template #item="{ element }">
            <li class="mb-2">
                <SessionItem :session="element" />
            </li>
        </template>
    </Draggable>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useSessionsStore } from "@/stores/sessions";
import { mapActions, mapWritableState } from "pinia";

import Draggable from "vuedraggable";
import SessionItem from "./SessionItem.vue";

export default defineComponent({
    name: "SessionList",
    components: {
        Draggable,
        SessionItem,
    },
    computed: {
        ...mapWritableState(useSessionsStore, ["sessions"]),
    },
    methods: {
        ...mapActions(useSessionsStore, ["getSessions"]),
    },
    async created() {
        await this.getSessions();
    },
});
</script>
