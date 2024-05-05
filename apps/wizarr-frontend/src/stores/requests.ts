import type { Request, Requests } from "@/types/api/request";
import { defineStore } from "pinia";

// Interface for the state shape of the store
interface RequestsStoreState {
    requests: Requests;
}

// Define and export a store for handling request data
export const useRequestsStore = defineStore("requests", {
    // Initial state setup for the store
    state: (): RequestsStoreState => ({
        requests: [],
    }),
    // Actions that can be called to manipulate the state
    actions: {
        // Asynchronously fetches requests from the server and updates the store
        async getRequests() {
            try {
                const response = await this.$axios.get<Request[]>("/api/requests");
                const receivedRequests = response.data || [];

                // Update or add new requests in the store
                this.requests = receivedRequests.reduce((acc: Request[], request: Request) => {
                    const index = acc.findIndex(r => r.id === request.id);
                    if (index !== -1) {
                        acc[index] = request; // Update existing request
                    } else {
                        acc.push(request); // Add new request
                    }
                    return acc;
                }, this.requests.slice()); // Use a slice to create a copy and avoid mutation during iteration

                // Remove any requests that no longer exist in the backend
                this.requests = this.requests.filter(r => receivedRequests.some(req => req.id === r.id));
            } catch (error) {
                this.$toast.error("Could not get requests"); // Notify the user of failure to fetch requests
                console.error(error);
            }
        },
        // Asynchronously creates a new request on the server and adds it to the store
        async createRequest(requestData: Request) {
            try {
                const formData = new FormData();
                Object.entries(requestData).forEach(([key, value]) => formData.append(key, value));

                const response = await this.$axios.post<Request>("/api/requests", formData);
                if (response.data) {
                    this.requests.push(response.data); // Add the newly created request to the store
                    return response.data; // Return the newly created request data
                }
            } catch (error) {
                this.$toast.error("Could not create request"); // Notify the user of failure to create request
                console.error(error);
            }
        },
        // Asynchronously deletes a request from the server and removes it from the store
        async deleteRequest(id: number) {
            try {
                await this.$axios.delete(`/api/requests/${id}`);
                const index = this.requests.findIndex(request => request.id === id);
                if (index !== -1) {
                    this.requests.splice(index, 1); // Remove the request from the store if found
                }
            } catch (error) {
                this.$toast.error("Could not delete request"); // Notify the user of failure to delete request
                console.error(error);
            }
        },
    },
    persist: true, // Enable persistence for the store to maintain state across sessions
});
