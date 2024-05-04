import type { Request, Requests } from "@/types/api/request";
import { defineStore } from "pinia";

interface RequestsStoreState {
    requests: Requests;
}

export const useRequestsStore = defineStore("requests", {
    state: (): RequestsStoreState => ({
        requests: [],
    }),
    actions: {
        async getRequests() {
            try {
                const response = await this.$axios.get<Request[]>("/api/requests");
                const receivedRequests = response.data || [];

                // Sync the store with the received data
                this.requests = receivedRequests.reduce((acc: Request[], request: Request) => {
                    const index = acc.findIndex(r => r.id === request.id);
                    if (index !== -1) {
                        acc[index] = request; // Update existing request
                    } else {
                        acc.push(request); // Add new request
                    }
                    return acc;
                }, this.requests.slice());

                // Remove obsolete requests
                this.requests = this.requests.filter(r => receivedRequests.some(req => req.id === r.id));
            } catch (error) {
                this.$toast.error("Could not get requests");
                console.error(error);
            }
        },
        async createRequest(requestData: Request) {
            try {
                const formData = new FormData();
                Object.entries(requestData).forEach(([key, value]) => formData.append(key, value));

                const response = await this.$axios.post<Request>("/api/requests", formData);
                if (response.data) {
                    this.requests.push(response.data);
                    return response.data;
                }
            } catch (error) {
                this.$toast.error("Could not create request");
                console.error(error);
            }
        },
        async deleteRequest(id: number) {
            try {
                await this.$axios.delete(`/api/requests/${id}`);
                const index = this.requests.findIndex(request => request.id === id);
                if (index !== -1) {
                    this.requests.splice(index, 1);
                }
            } catch (error) {
                this.$toast.error("Could not delete request");
                console.error(error);
            }
        },
    },
    persist: true,
});
