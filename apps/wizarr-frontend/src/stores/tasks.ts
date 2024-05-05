import { defineStore } from 'pinia';
import type { Job, JobList } from '@/types/Tasks';

// Interface defining the state structure for the tasks store
interface TasksStoreState {
    jobs: JobList;
}

// Define and export a store for handling job tasks
export const useTasksStore = defineStore('tasks', {
    // Initial state setup for the store
    state: (): TasksStoreState => ({
        jobs: [],
    }),
    // Actions that can be called to manipulate the state
    actions: {
        // Generic method to fetch, update, or delete jobs based on provided parameters
        async fetchAndUpdateJobs(url: string, method: 'GET' | 'POST' | 'DELETE' = 'GET', payload?: any) {
            try {
                // Perform the API call using Axios with the provided method, URL, and payload
                const response = await this.$axios({
                    url,
                    method,
                    data: payload ? JSON.stringify(payload) : undefined,
                });
                const jobData: Job | Job[] = response.data;
                if (!jobData) {
                    throw new Error('No job data received');
                }

                // Check if the response contains an array of jobs or a single job
                if (Array.isArray(jobData)) {
                    // Replace all jobs with the new array from the response
                    this.jobs = jobData;
                } else {
                    // Update an existing job or add a new one to the list
                    const index = this.jobs.findIndex(job => job.id === jobData.id);
                    if (index !== -1) {
                        this.jobs[index] = jobData;  // Update the existing job
                    } else {
                        this.jobs.push(jobData);  // Add the new job to the list
                    }
                }
                return jobData;  // Return the job data for further processing
            } catch (error) {
                // Handle errors and log them
                const errorMessage = (error as Error).message;
                this.$toast.error(`Could not perform action on job: ${errorMessage}`);
                console.error(error);
                return null;
            }
        },

        // Specific actions to interact with jobs through API calls
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

        // Deletes a job and removes it from the local state if successful
        async deleteJob(id: string) {
            const jobData = await this.fetchAndUpdateJobs(`/api/scheduler/jobs/${id}`, 'DELETE');
            if (jobData !== null) {
                const index = this.jobs.findIndex(job => job.id === id);
                if (index !== -1) {
                    this.jobs.splice(index, 1);  // Remove the job from the list
                }
            }
            return jobData;  // Return the job data, which should be null after deletion
        },
    },
    persist: true,  // Enable persistence for the store to maintain state across sessions
});
