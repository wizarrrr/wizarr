<template>
    <WidgetTemplate>
        <div class="flex flex-row-reverse justify-between p-3">
            <div class="text-left flex-grow text-xl leading-tight tracking-tight md:text-2xl">
                <div class="text-gray-400 dark:text-gray-300 mb-0 font-bold">404 Error</div>
                <div class="text-gray-300 dark:text-gray-200 text-lg font-normal">Could not find the widget.</div>
            </div>
        </div>
    </WidgetTemplate>
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
