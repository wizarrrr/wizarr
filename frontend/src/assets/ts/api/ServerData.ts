import axios from "../utils/Axios";

export interface Server {
    settings: ServerSettings;
    version: string;
    update_available: boolean;
    debug: boolean;
    setup_required: boolean;
}

export interface ServerSettings {
    server_name: string;
    server_url: string;
    server_type: "jellyfin" | "plex";
    server_verified: string;
}

export default async () => {
    // Get health status from backend
    const response = await axios.get("/api/server");

    // If response is not 200, raise error
    if (response.status !== 200) {
        throw new Error("Could not connect to backend");
    }

    // Return health data from backend
    return response.data as Partial<Server>;
};
