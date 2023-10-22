<template>
    <div>
        <MediaForm v-bind="$attrs" :setup="true" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

import MediaForm from '@/modules/settings/components/Forms/MediaForm.vue';

export default defineComponent({
    name: 'MediaServerView',
    components: {
        MediaForm,
    },
});
</script>
