import axios from "../utils/Axios";

export interface HealthData {
    uptime?: string;
    status?: string;
    version?: string;
    update_available?: boolean;
    current_user?: any;
    debug?: boolean;
    setup_required?: boolean;
}

export default async () => {
    // Get health status from backend
    const response = await axios.get("/api/health");

    // If response is not 200, raise error
    if (response.status !== 200) {
        throw new Error("Could not connect to backend");
    }

    // Return health data from backend
    return response.data as HealthData;
};
