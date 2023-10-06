<template>
    <Draggable v-if="requests && requests.length > 0" v-model="requests" tag="ul" group="requests" ghost-class="moving-card" :animation="200" item-key="id">
        <template #item="{ element }">
            <li class="mb-2">
                <RequestsItem :request="element" />
            </li>
        </template>
    </Draggable>
    <div v-else class="flex flex-col justify-center items-center space-y-1">
        <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
        <span class="text-gray-400">{{ __("No Requests found") }}</span>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useRequestsStore } from "@/stores/requests";
import { mapActions, mapWritableState } from "pinia";

import Draggable from "vuedraggable";
import RequestsItem from "./RequestsItem.vue";

export default defineComponent({
    name: "RequestsList",
    components: {
        Draggable,
        RequestsItem,
    },
    computed: {
        ...mapWritableState(useRequestsStore, ["requests"]),
    },
    methods: {
        ...mapActions(useRequestsStore, ["getRequests"]),
    },
    async created() {
        await this.getRequests();
    },
});
</script>
