<template>
    <WidgetTemplate icon="fa-solid fa-exclamation-triangle" title="Error" value="Something went wrong." />
</template>

<script lang="ts">
import { defineComponent } from "vue";
import WidgetTemplate from "@/templates/WidgetTemplate.vue";

export default defineComponent({
    name: "ErrorWidget",
    components: {
        WidgetTemplate,
    },
});
</script>
