import Toastify from "toastify-js";

declare type ScanLibrariesOptions = {
    container: string | Element;
    server: ScanLibrariesServer;
    error: string | Element | null;
};

declare type ScanLibrariesServer = {
    url: string;
    type: ScanLibrariesServerType;
    api_key: string;
};

declare type ScanLibrariesServerType = "jellyfin" | "plex";

class ScanLibraries {

    private container: string | Element;
    private server: ScanLibrariesServer;
    private error: string | Element | null;

    private api_endpoint: string = "/api/scan-libraries";
    
    constructor(options: ScanLibrariesOptions) {
        this.container = options.container;
        this.server = options.server;
        this.error = options.error || null;

        try {
            this.init();
            this.initContainer();
            this.initError();
        } catch (error) {
            let message = "Not initialized";
            
            if (error instanceof Error) {
                message = error.message;
            }

            console.error(message);
            this.pushError(message);
        }
    }

    private init(): void {
        if (typeof this.server.type !== "string") {
            throw new Error("Server type is not a string");
        }

        if (!(this.server.type === "jellyfin" || this.server.type === "plex")) {
            throw new Error("Server type is not valid");
        }

        if (typeof this.server.url !== "string") {
            throw new Error("Server URL is not a string");
        }

        if (typeof this.server.api_key !== "string") {
            throw new Error("Server API key is not a string");
        }

        console.info("Scan Libraries has been initialized");
    }

    private initContainer(): void {
        if (typeof this.container === "string") {
            const container = document.querySelector(this.container);
            if (container) {
                this.container = container;
            }
        }
    }

    private initError(): void {
        if (typeof this.error === "string") {
            const error = document.querySelector(this.error);
            if (error) {
                this.error = error;
            }
        }
    }

    public async scan(): Promise<void> {
        const formData = new FormData();

        formData.append("server_type", this.server.type);
        formData.append("server_url", this.server.url);
        formData.append("server_api_key", this.server.api_key);

        const response = await fetch(this.api_endpoint, {
            method: "POST",
            body: formData
        });

        if (response.status === 400) {
            this.pushError("Bad request");
            return;
        }

        if (response.status === 401) {
            this.pushError("Unauthorized");
            return;
        }

        if (response.status === 404) {
            this.pushError("Not found");
            return;
        }

        if (response.status === 500) {
            this.pushError("Internal server error");
            return;
        }

        if (response.status === 200) {
            return response.json();
        }
    }

    private pushError(message: string): void {
        console.error(message);
        Toastify({ text: `Scan Libraries: ${message}`, backgroundColor: '#dc3545', duration: 3000, gravity: 'bottom', position: 'right', className: 'toast', stopOnFocus: true }).showToast();
    }
}

export default ScanLibraries;