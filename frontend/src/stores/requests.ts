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
            // Get the requests from the API
            const requests = await this.$axios.get<any, { data: Request[] }>("/api/requests").catch((err) => {
                this.$toast.error("Could not get requests");
                return null;
            });

            // If the requests are null, return
            if (requests === null) return;

            // Update the requests that are already in the store
            this.requests.forEach((request, index) => {
                const new_request = requests.data.find((new_request: Request) => new_request.id === request.id);
                if (new_request) this.requests[index] = new_request;
            });

            // Add the new requests to the store if they don't exist
            requests.data.forEach((request: Request) => {
                if (!this.requests.find((old_request) => old_request.id === request.id)) this.requests.push(request);
            });

            // Remove the requests that were not in the response
            this.requests.forEach((request, index) => {
                if (!requests.data.find((new_request: Request) => new_request.id === request.id)) this.requests.splice(index, 1);
            });
        },
        async createRequest(request: Request) {
            // Convert the request to a FormData object
            const formData = new FormData();

            Object.keys(request).forEach((key) => {
                // @ts-ignore
                formData.append(key, request[key]);
            });

            // Create the request
            const response = await this.$axios.post("/api/requests", formData, { disableErrorToast: true }).catch((err) => {
                this.$toast.error("Could not create request");
                console.error(err);
                return null;
            });

            // If the response is null, return
            if (response === null) return;

            // Add the request to the store
            this.requests.push(response.data as Request);

            // Return the request
            return response.data as Request;
        },
        async deleteRequest(id: number) {
            // Delete the request from the API
            await this.$axios.delete(`/api/requests/${id}`).catch((err) => {
                this.$toast.error("Could not delete request");
                console.error(err);
                return null;
            });

            // Remove the request from the store
            const index = this.requests.findIndex((request: Request) => request.id === id);
            if (index !== -1) this.requests.splice(index, 1);
        },
    },
    persist: true,
});
