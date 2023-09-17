<template>
    <TaskList />
</template>

<script lang="ts">
import { defineComponent } from "vue";

import TaskList from "@/components/TaskList/TaskList.vue";

export default defineComponent({
    name: "TasksView",
    components: {
        TaskList,
    },
});
</script>
