<template>
    <div class="flex flex-col space-y-4">
        <RequestsList />

        <div class="fixed right-6 bottom-6 group">
            <FormKit type="button" :classes="{ input: '!w-14 !h-14' }" @click="createRequest">
                <i class="fas fa-plus text-xl transition-transform group-hover:rotate-45"></i>
            </FormKit>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

import RequestsList from "../components/Requests/Requests.vue";
import RequestsForm from "../components/Forms/RequestForm.vue";

export default defineComponent({
    name: "Requests",
    components: {
        RequestsList,
    },
    methods: {
        createRequest() {
            this.$modal.openModal(RequestsForm, {
                title: this.__("Add Request Service"),
                disableFooter: true,
            });
        },
    },
});
</script>
