<template>
    <div class="flex flex-col space-y-3">
        <template v-for="changeLog in getSortedChangeLogsSized">
            <ChangeLogItem :changeLog="changeLog" />
        </template>
        <button @click="loadMore" type="button" class="block mb-2 text-sm font-medium text-secondary dark:text-primary">
            {{ __("Load More") }}
        </button>
    </div>
</template>

<script lang="ts">
import { mapActions, mapState } from "pinia";
import { defineComponent } from "vue";
import { useChangeLogStore } from "@/stores/changeLog";

import ChangeLogItem from "./ChangeLogItem.vue";
import DefaultButton from "@/components/Buttons/DefaultButton.vue";

export default defineComponent({
    name: "ChangeLogs",
    components: {
        ChangeLogItem,
        DefaultButton,
    },
    data() {
        return {
            size: 5,
            page: 1,
        };
    },
    methods: {
        async loadMore() {
            this.page++;
            await this.getChangeLogs(this.size, this.page);
        },
        ...mapActions(useChangeLogStore, ["getChangeLogs"]),
    },
    computed: {
        getSortedChangeLogsSized() {
            return this.getSortedChangeLogs.slice(0, this.size * this.page);
        },
        ...mapState(useChangeLogStore, ["getSortedChangeLogs"]),
    },
    async mounted() {
        this.getChangeLogs(this.size, this.page);
    },
});
</script>
