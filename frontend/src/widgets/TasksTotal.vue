<template>
    <WidgetTemplate :title="__('Total Tasks')" :value="count" icon="fa-server" />
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useTasksStore } from "@/stores/tasks";
import { mapState } from "pinia";

import WidgetTemplate from "@/templates/WidgetTemplate.vue";

export default defineComponent({
    name: "TasksTotal",
    components: {
        WidgetTemplate,
    },
    computed: {
        count() {
            return String(this.jobs.length);
        },
        ...mapState(useTasksStore, ["jobs"]),
    },
});
</script>
