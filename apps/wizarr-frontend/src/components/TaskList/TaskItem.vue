<template>
    <ListItem :class="{ 'inner-border inner-border-red-600 inner-border-[2px]': failedTask }" icon="fa-list">
        <template #title>
            <span class="text-lg">{{ $filters(["underscroreSpaces", "titleCase"], task.name) }}</span>
            <p class="text-xs truncate text-gray-500 dark:text-gray-400 w-full">
                {{ formattedCountdown }}
            </p>
        </template>

        <template #buttons>
            <div class="flex flex-row space-x-2">
                <div class="w-[36px] h-[36px]">
                    <button :disabled="buttonsDisabled.run" @click="runLocalJob" v-if="job.next_run_time != null" class="w-full h-full bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-secondary dark:hover:bg-secondary_hover">
                        <i class="fa-solid fa-refresh ml-[-2px]"></i>
                    </button>
                </div>
                <div class="w-[36px] h-[36px]">
                    <button :disabled="buttonsDisabled.resume" @click="resumeLocalJob" v-if="job.next_run_time == null" class="w-full h-full bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-secondary dark:hover:bg-secondary_hover">
                        <i class="fa-solid fa-play"></i>
                    </button>
                    <button :disabled="buttonsDisabled.pause" @click="pauseLocalJob" v-else class="w-full h-full bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-secondary dark:hover:bg-secondary_hover">
                        <i class="fa-solid fa-pause"></i>
                    </button>
                </div>
            </div>
            <div class="flex flex-row space-x-2">
                <!-- <button class="bg-secondary hover:bg-secondary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-secondary dark:hover:bg-secondary_hover">
                    <i class="fa-solid fa-edit"></i>
                </button> -->
                <button :disabled="buttonsDisabled.delete" @click="deleteLocalJob" class="bg-red-600 hover:bg-primary_hover focus:outline-none text-white font-medium rounded px-3.5 py-2 text-sm dark:bg-red-600 dark:hover:bg-primary_hover">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        </template>
    </ListItem>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { useTasksStore } from "@/stores/tasks";
import { mapActions } from "pinia";

import type { Job } from "@/types/Tasks";

import ListItem from "../ListItem.vue";

import moment from "moment";

export default defineComponent({
    name: "TaskItem",
    components: {
        ListItem,
    },
    props: {
        task: {
            type: Object as () => Job,
            required: true,
        },
    },
    data() {
        return {
            job: this.task,
            countdown: "Pending",
            failedTask: false,
            intervals: [] as number[],
            buttonsDisabled: {
                run: false,
                pause: false,
                resume: false,
                delete: false,
            },
        };
    },
    computed: {
        formattedCountdown(): string {
            return this.countdown.length > 0 ? this.countdown : this.failedTask ? "Failed" : "Pending";
        },
    },
    methods: {
        async runLocalJob() {
            // Disable the run button
            this.buttonsDisabled.run = true;

            // Run the job
            const job = await this.runJob(this.task.id);

            // Update the job
            await this.restartCountdown(job);

            // Show toast
            this.$toast.info("Task has been run.");

            // Enable the run button
            this.buttonsDisabled.run = false;
        },
        async pauseLocalJob() {
            // Disable the pause button
            this.buttonsDisabled.pause = true;

            // Pause the job
            const job = await this.pauseJob(this.task.id);

            // Update the job
            await this.restartCountdown(job);

            // Show toast
            this.$toast.info("Task has been paused.");

            // Enable the pause button
            this.buttonsDisabled.pause = false;
        },
        async resumeLocalJob() {
            // Disable the resume button
            this.buttonsDisabled.resume = true;

            // Resume the job
            const job = await this.resumeJob(this.task.id);

            // Update the job
            await this.restartCountdown(job);

            // Show toast
            this.$toast.info("Task has been resumed.");

            // Enable the resume button
            this.buttonsDisabled.resume = false;
        },
        async deleteLocalJob() {
            // Disable all buttons
            Object.keys(this.buttonsDisabled).forEach((key) => {
                (this.buttonsDisabled as any)[key] = true;
            });

            // Delete the job
            await this.deleteJob(this.task.id);

            // Show toast
            this.$toast.info("Task has been deleted.");
        },
        async createCountdown() {
            // Get the next run time and the current time
            const nextRunTime = new Date(this.job.next_run_time);
            const now = new Date();

            // Find the distance between now and then using moment.js
            const distance = moment(nextRunTime).diff(moment(now));

            // If the distance is negative, the task is overdue
            if (distance < 0) {
                this.stopCountdown();
                await this.restartCountdown();
            }

            // Show the time left
            this.updateCoundown(now, nextRunTime);
        },
        async startCountdown() {
            // Check if the task is paused by checking if next_run_time is null
            if (this.job.next_run_time === null) {
                this.countdown = "Paused";
                this.stopCountdown();
                return;
            }

            // Create the interval and add it to the intervals array
            const interval = setInterval(this.createCountdown, 1000);
            this.intervals.push(interval as unknown as number);
        },
        async stopCountdown() {
            // Cycle through all the intervals and clear them
            // We use an array because if we accidentally create multiple intervals, we can clear them all
            this.intervals.forEach((interval) => {
                clearInterval(interval);
                this.intervals.splice(this.intervals.indexOf(interval), 1);
            });
        },
        async restartCountdown(job?: Job) {
            // Update the job if no job is passed
            job = job ?? (await this.getJob(this.task.id));

            // If the job is null, the task is not scheduled
            if (job === null || job === undefined) {
                this.failedTask = true;
                this.stopCountdown();
                return;
            }

            this.job = job;
            this.startCountdown();
        },
        async updateCoundown(now: Date, then: Date) {
            // Find the distance between now and then using moment.js
            const distance = moment(then).diff(moment(now));

            // Time calculations for days, hours, minutes and seconds using moment.js
            const days = moment.duration(distance).days();
            const hours = moment.duration(distance).hours();
            const minutes = moment.duration(distance).minutes();
            const seconds = moment.duration(distance).seconds();

            // String representation of the time left, ignoring values that are 0
            const timeLeft = [];
            if (days > 0) timeLeft.push(`${days}d`);
            if (hours > 0) timeLeft.push(`${hours}h`);
            if (minutes > 0) timeLeft.push(`${minutes}m`);
            if (seconds > 0) timeLeft.push(`${seconds}s`);

            // Return the time left as a string
            this.countdown = timeLeft.join(" ");
        },
        ...mapActions(useTasksStore, ["getJob", "runJob", "pauseJob", "resumeJob", "deleteJob"]),
    },
    mounted() {
        // Get the next run time and the current time
        const nextRunTime = new Date(this.job.next_run_time);
        const now = new Date();

        // Set and start the countdown
        this.updateCoundown(now, nextRunTime);
        this.startCountdown();
    },
    beforeUnmount() {
        // Stop the countdown
        this.stopCountdown();
    },
});
</script>
