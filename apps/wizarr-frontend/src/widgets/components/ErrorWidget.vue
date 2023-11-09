<template>
    <DefaultWidget icon="fa-solid fa-exclamation-triangle" title="Error" value="Something went wrong." />
</template>

<script lang="ts">
import { defineComponent } from "vue";
import DefaultWidget from "@/widgets/templates/DefaultWidget.vue";

export default defineComponent({
    name: "ErrorWidget",
    components: {
        DefaultWidget,
    },
});
</script>
