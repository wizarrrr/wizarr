<template>
    <GraphWidget
        icon="fa-solid fa-envelope"
        title="Invitations Created"
        :value="String(invitations.length)"
        :chart-data="lineChartData"
        :options="options"
    />
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapState } from 'pinia';
import { useInvitationStore } from '@/stores/invitations';
import { Chart, registerables } from 'chart.js';

import type { ChartOptions } from 'chart.js';

import moment from 'moment';

import GraphWidget from '@/widgets/templates/GraphWidget.vue';

Chart.register(...registerables);

export default defineComponent({
    name: 'InvitesGraph',
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
            this.invitations.forEach((invitation) => {
                // Get the day of the week the invitation was created starting at 0 for Monday
                const day = moment(invitation.created_at).day();
                // Increment the count for that day
                counts[day]++;
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
                        label: 'Invitation Created',
                        data: this.countsArray,
                        fill: false,
                        borderColor: 'rgb(254 65 85)',
                        tension: 0.1,
                    },
                ],
            };
        },
        ...mapState(useInvitationStore, ['invitations']),
    },
});
</script>
