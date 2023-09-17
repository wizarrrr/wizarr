<template>
    <SessionList />
</template>

<script lang="ts">
import { defineComponent } from "vue";

import SessionList from "@/components/SessionList/SessionList.vue";

export default defineComponent({
    name: "SessionsView",
    components: {
        SessionList,
    },
});
</script>
