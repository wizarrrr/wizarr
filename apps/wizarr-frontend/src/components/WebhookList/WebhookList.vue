<template>
    <Draggable v-if="webhooks && webhooks.length > 0" v-model="webhooks" tag="ul" group="webhooks" ghost-class="moving-card" :animation="200" item-key="id">
        <template #item="{ element }">
            <li class="mb-2">
                <WebhookItem :webhook="element" />
            </li>
        </template>
    </Draggable>
    <div v-else class="flex flex-col justify-center items-center space-y-1">
        <i class="fa-solid fa-info-circle text-3xl text-gray-400"></i>
        <span class="text-gray-400">{{ __("No Webhooks found") }}</span>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useWebhookStore } from "@/stores/webhooks";
import { mapActions, mapWritableState } from "pinia";

import Draggable from "vuedraggable";
import WebhookItem from "./WebhookItem.vue";

export default defineComponent({
    name: "WebhookList",
    components: {
        Draggable,
        WebhookItem,
    },
    computed: {
        ...mapWritableState(useWebhookStore, ["webhooks"]),
    },
    methods: {
        ...mapActions(useWebhookStore, ["getWebhooks"]),
    },
    async created() {
        await this.getWebhooks();
    },
});
</script>
