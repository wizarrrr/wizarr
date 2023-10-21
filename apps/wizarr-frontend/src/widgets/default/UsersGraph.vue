<template>
    <GraphWidget
        icon="fa-solid fa-users"
        title="Users Created"
        :value="String(users.length)"
        :chart-data="lineChartData"
        :options="options"
    />
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapState } from 'pinia';
import { useUsersStore } from '@/stores/users';
import { Chart, registerables } from 'chart.js';

import type { ChartOptions } from 'chart.js';

import moment from 'moment';

import GraphWidget from '@/widgets/templates/GraphWidget.vue';

Chart.register(...registerables);

export default defineComponent({
    name: 'UsersGraph',
    components: {
        GraphWidget,
    },
    data() {
        return {
            options: {
                responsive: true, // Make the chart responsive
                maintainAspectRatio: false, // Do not maintain aspect ratio
                scales: {
                    x: {
                        grid: {
                            display: false,
                        },
                    },
                    y: {
                        display: false,
                    },
                },
                plugins: {
                    legend: {
                        display: false,
                    },
                },
            } as ChartOptions,
        };
    },
    computed: {
        // Create an array of the user counts for each day of the week
        countsArray() {
            const counts = [0, 0, 0, 0, 0, 0, 0];
            this.users.forEach((user) => {
                const day = moment(user.created).day();
                counts[day] += 1;
            });
            return counts.reverse();
        },
        lineChartData() {
            return {
                labels: [
                    'Monday',
                    'Tuesday',
                    'Wednesday',
                    'Thursday',
                    'Friday',
                    'Saturday',
                    'Sunday',
                ],
                datasets: [
                    {
                        label: 'Users Created',
                        data: this.countsArray,
                        fill: false,
                        borderColor: 'rgb(254 65 85)',
                        tension: 0.1,
                    },
                ],
            };
        },
        ...mapState(useUsersStore, ['users']),
    },
});
</script>
