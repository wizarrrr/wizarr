<template>
    <div class="flex flex-col space-y-2">
        <template v-for="request in requests">
            <ListItem :svg-string="request.icon">
                <template #title>
                    <span class="text-lg">{{ request.name }}</span>
                </template>
                <template #buttons>
                    <div class="flex flex-row space-x-2">
                        <FormKit type="button" data-theme="secondary" @click="openURL(request.url)" :classes="{ input: '!bg-secondary !px-3.5 h-[36px]' }">
                            <i class="fa-solid fa-external-link"></i>
                        </FormKit>
                    </div>
                </template>
            </ListItem>
        </template>
    </div>
</template>

<script lang="ts">
import type { Requests, Request } from "@/types/api/request";
import { defineComponent } from "vue";
import ListItem from "@/components/ListItem.vue";

interface CustomRequest extends Request {
    icon: string;
}

export default defineComponent({
    name: "RequestsList",
    components: {
        ListItem,
    },
    props: {
        requestURLS: {
            type: Array as () => Requests,
            required: true,
        },
    },
    data() {
        return {
            requests: [] as CustomRequest[],
        };
    },
    methods: {
        openURL(url: string) {
            window.open(url, "_blank");
        },
        async loadIcon(request: Request) {
            return await import(`../../../assets/img/logo/${request.service}.svg?raw`);
        },
    },
    async beforeMount() {
        const requests = this.requestURLS;

        requests.forEach(async (request) => {
            const icon = await this.loadIcon(request);

            this.requests.push({
                ...request,
                icon: icon.default ?? "",
            });
        });
    },
});
</script>
