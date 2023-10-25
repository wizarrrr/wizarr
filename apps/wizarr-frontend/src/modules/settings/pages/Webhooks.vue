<template>
    <WebhookList />
    <div class="fixed right-6 bottom-6 group">
        <FormKit type="button" :classes="{ input: '!w-14 !h-14' }" @click="createWebhook">
            <i class="fas fa-plus text-xl transition-transform group-hover:rotate-45"></i>
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import WebhookList from "@/components/WebhookList/WebhookList.vue";
import WebhookForm from "../components/Forms/WebhookForm.vue";

export default defineComponent({
    name: "WebhooksView",
    components: {
        WebhookList,
    },
    methods: {
        createWebhook() {
            this.$modal.openModal(WebhookForm, {
                title: this.__("Create Webhook"),
                disableFooter: true,
            });
        },
    },
});
</script>
