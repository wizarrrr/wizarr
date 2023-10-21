<template>
    <DefaultWidget :title="__('Total Tasks')" :value="count" icon="fa-server" />
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useTasksStore } from '@/stores/tasks';
import { mapState } from 'pinia';

import DefaultWidget from '@/widgets/templates/DefaultWidget.vue';

export default defineComponent({
    name: 'TasksTotal',
    components: {
        DefaultWidget,
    },
    computed: {
        count() {
            return String(this.jobs.length);
        },
        ...mapState(useTasksStore, ['jobs']),
    },
});
</script>
