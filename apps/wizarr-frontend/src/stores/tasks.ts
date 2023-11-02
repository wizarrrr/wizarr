import { defineStore } from 'pinia';
import type { Job, JobList } from '@/types/Tasks';

interface TasksStoreState {
    jobs: JobList;
}

export const useTasksStore = defineStore('tasks', {
    state: (): TasksStoreState => ({
        jobs: [],
    }),
    actions: {
        async getJobs() {
            // Get the jobs from the API
            const jobs = await this.$axios
                .get('/api/scheduler/jobs')
                .catch((err) => {
                    this.$toast.error('Could not get jobs');
                    return null;
                });

            // If the jobs are null, return
            if (jobs === null) return;

            // Update the jobs that are already in the store
            this.jobs.forEach((job, index) => {
                const new_job = jobs.data.find(
                    (new_job: Job) => new_job.id === job.id,
                );
                if (new_job) this.jobs[index] = new_job;
            });

            // Add the new jobs to the store if they don't exist
            jobs.data.forEach((job: Job) => {
                if (!this.jobs.find((old_job: Job) => old_job.id === job.id))
                    this.jobs.push(job);
            });

            // Remove the jobs that were not in the response
            this.jobs.forEach((job, index) => {
                if (!jobs.data.find((new_job: Job) => new_job.id === job.id))
                    this.jobs.splice(index, 1);
            });

            // Return the jobs
            return jobs.data as JobList;
        },
        async getJob(id: string) {
            // Get the job from the API
            const job = await this.$axios
                .get(`/api/scheduler/jobs/${id}`)
                .catch((err) => {
                    this.$toast.error('Could not get job');
                    console.error(err);
                    return null;
                });

            // If the job is null, return
            if (job === null) return;

            // Update the job in the store
            const index = this.jobs.findIndex((job: Job) => job.id === id);
            if (index !== -1) this.jobs[index] = job.data;

            // Return the job
            return job.data as Job;
        },
        async runJob(id: string) {
            // Run the job
            const job = await this.$axios
                .post(`/api/scheduler/jobs/${id}/run`)
                .catch((err) => {
                    this.$toast.error('Could not run job');
                    console.error(err);
                    return null;
                });

            // If the job is null, return
            if (job === null) return;

            // Update the job in the store
            const index = this.jobs.findIndex((job: Job) => job.id === id);
            if (index !== -1) this.jobs[index] = job.data;

            // Return the job
            return job.data as Job;
        },
        async pauseJob(id: string) {
            // Pause the job
            const job = await this.$axios
                .post(`/api/scheduler/jobs/${id}/pause`)
                .catch((err) => {
                    this.$toast.error('Could not pause job');
                    console.error(err);
                    return null;
                });

            // If the job is null, return
            if (job === null) return;

            // Update the job in the store
            const index = this.jobs.findIndex((job: Job) => job.id === id);
            if (index !== -1) this.jobs[index] = job.data;

            // Return the job
            return job.data as Job;
        },
        async resumeJob(id: string) {
            // Resume the job
            const job = await this.$axios
                .post(`/api/scheduler/jobs/${id}/resume`)
                .catch((err) => {
                    this.$toast.error('Could not resume job');
                    console.error(err);
                    return null;
                });

            // If the job is null, return
            if (job === null) return;

            // Update the job in the store
            const index = this.jobs.findIndex((job: Job) => job.id === id);
            if (index !== -1) this.jobs[index] = job.data;

            // Return the job
            return job.data as Job;
        },
        async deleteJob(id: string) {
            // Delete the job
            const job = await this.$axios
                .delete(`/api/scheduler/jobs/${id}`)
                .catch((err) => {
                    this.$toast.error('Could not delete job');
                    console.error(err);
                    return null;
                });

            // If the job is null, return
            if (job === null) return;

            // Update the job in the store
            const index = this.jobs.findIndex((job: Job) => job.id === id);
            if (index !== -1) this.jobs.splice(index, 1);

            // Return the job
            return job.data as Job;
        },
    },
    persist: true,
});
