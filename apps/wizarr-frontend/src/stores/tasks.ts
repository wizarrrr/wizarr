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
        async fetchAndUpdateJobs(url: string, method: 'GET' | 'POST' | 'DELETE' = 'GET', payload?: any) {
            try {
                const response = await this.$axios({
                    url,
                    method,
                    data: payload ? JSON.stringify(payload) : undefined,
                });
                const jobData: Job | Job[] = response.data;
                if (!jobData) {
                    throw new Error('No job data received');
                }

                if (Array.isArray(jobData)) {
                    // If it's an array, replace all jobs
                    this.jobs = jobData;
                } else {
                    // If it's a single job, update or add it to the list
                    const index = this.jobs.findIndex(job => job.id === jobData.id);
                    if (index !== -1) {
                        this.jobs[index] = jobData;
                    } else {
                        this.jobs.push(jobData);
                    }
                }
                return jobData;
            } catch (error) {
                const errorMessage = (error as Error).message;
                this.$toast.error(`Could not perform action on job: ${errorMessage}`);
                console.error(error);
                return null;
            }
        },

        getJobs() {
            return this.fetchAndUpdateJobs('/api/scheduler/jobs');
        },

        getJob(id: string) {
            return this.fetchAndUpdateJobs(`/api/scheduler/jobs/${id}`);
        },

        runJob(id: string) {
            return this.fetchAndUpdateJobs(`/api/scheduler/jobs/${id}/run`, 'POST');
        },

        pauseJob(id: string) {
            return this.fetchAndUpdateJobs(`/api/scheduler/jobs/${id}/pause`, 'POST');
        },

        resumeJob(id: string) {
            return this.fetchAndUpdateJobs(`/api/scheduler/jobs/${id}/resume`, 'POST');
        },

        async deleteJob(id: string) {
            const jobData = await this.fetchAndUpdateJobs(`/api/scheduler/jobs/${id}`, 'DELETE');
            if (jobData !== null) {
                const index = this.jobs.findIndex(job => job.id === id);
                if (index !== -1) {
                    this.jobs.splice(index, 1);
                }
            }
            return jobData;
        },
    },
    persist: true,
});
