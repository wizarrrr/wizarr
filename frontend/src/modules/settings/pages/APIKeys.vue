<template>
    <APIKeyList />
    <div class="fixed right-6 bottom-6 group">
        <FormKit type="button" :classes="{ input: '!w-14 !h-14' }" @click="createAPIKey">
            <i class="fas fa-plus text-xl transition-transform group-hover:rotate-45"></i>
        </FormKit>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import APIKeyList from "@/components/APIKeyList/APIKeyList.vue";
import APIKeyForm from "@/components/Forms/APIKeyForm.vue";

export default defineComponent({
    name: "APIKeysView",
    components: {
        APIKeyList,
    },
    methods: {
        createAPIKey() {
            this.$modal.openModal(APIKeyForm, {
                title: this.__("Create API Key"),
                disableFooter: true,
            });
        },
    },
});
</script>
