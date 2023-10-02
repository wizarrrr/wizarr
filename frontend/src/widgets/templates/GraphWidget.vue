<template>
    <div class="w-full h-full">
        <LineChart :chart-data="chartData" :options="options" class="h-full pt-[70px]" />
        <WidgetTemplate :icon="String(icon)" :title="String(title)" :value="String(value)" class="p-2 absolute top-0 left-0 pointer-events-none" :class="class" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { LineChart } from "vue-chart-3";
import { Chart, registerables } from "chart.js";

import type { ChartData, ChartOptions } from "chart.js";

import WidgetTemplate from "@/widgets/templates/DefaultWidget.vue";

Chart.register(...registerables);

export default defineComponent({
    name: "GraphWidgetTemplate",
    components: {
        WidgetTemplate,
        LineChart,
    },
    props: {
        icon: {
            type: String,
            required: true,
        },
        title: {
            type: String,
            required: true,
        },
        value: {
            type: String,
            required: true,
        },
        chartData: {
            type: Object as () => ChartData<"line", number[], string>,
            required: true,
        },
        options: {
            type: Object as () => ChartOptions,
            required: true,
        },
        class: {
            type: Object as () => Record<string, string>,
            default: () => ({}),
            required: false,
        },
    },
});
</script>
