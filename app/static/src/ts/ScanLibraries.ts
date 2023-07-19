import Cookie from "js-cookie";
import Toastify from "toastify-js";

declare type ScanLibrariesOptions = {
    container: string | Element;
    count: string | Element;
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
    private count: string | Element;
    private server: ScanLibrariesServer;
    private error: string | Element | null;

    private api_endpoint: string = "/api/scan-libraries/";

    constructor(options: ScanLibrariesOptions) {
        this.container = options.container;
        this.count = options.count;
        this.server = options.server;
        this.error = options.error || null;

        try {
            this.init();
            this.initCount();
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

    private initCount(): void {
        if (typeof this.count === "string") {
            const count = document.querySelector(this.count);
            if (count) {
                this.count = count;
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
            body: formData,
            credentials: "same-origin",
            headers: {
                "X-CSRF-TOKEN": Cookie.get("csrf_access_token") ?? "",
            },
        });

        if (response.status !== 200) {
            let data = await response.json();

            if (data.message) {
                this.pushError(data.message);
                return;
            }

            this.pushError("Unknown error");
            return;
        }

        let data = await response.json();

        (this.container as Element).innerHTML = "";

        // Loop through data.libraries with key value and iteration
        let iteration = 0;

        // Place the element in the container
        for (const [key, value] of Object.entries(data.libraries)) {
            let library = this.createElement(key, value as string, iteration);
            (this.container as Element).appendChild(library);
            iteration++;
        }

        console.info("Scan Libraries has been scanned");

        // Set the count
        let length = String(Object.keys(data.libraries).length);
        (document.getElementById("library_count") as HTMLInputElement).value =
            length;
        console.info("Counted " + length + " libraries");
    }

    private createElement(
        title: string,
        value: string,
        iteration: number
    ): HTMLLIElement {
        const li = document.createElement("li");
        const input = document.createElement("input");

        input.type = "checkbox";
        input.id = "library_" + (iteration + 1);
        input.name = "library_" + (iteration + 1);
        input.value = value;
        input.classList.add("hidden", "peer");
        input.required = true;

        const label = document.createElement("label");
        label.htmlFor = "library_" + (iteration + 1);
        label.classList.add(
            // BACKGROUND
            "dark:peer-checked:bg-gray-600",
            "peer-checked:bg-gray-100",

            "dark:hover:bg-gray-600",
            "hover:bg-gray-100",

            "dark:bg-gray-700",
            "bg-gray-50",


            // TEXT
            "dark:peer-checked:text-gray-200",
            "peer-checked:text-gray-500",

            "dark:hover:text-gray-200",
            "hover:text-gray-500",

            "dark:text-gray-300",
            "text-gray-600",


            // BORDER            
            "dark:peer-checked:border-gray-700",
            "peer-checked:border-gray-50",

            "dark:hover:border-gray-600",
            "hover:border-gray-100",

            "dark:border-gray-600",
            "border-gray-100",

            // OTHER
            "border-2",
            "inline-flex",
            "items-center",
            "justify-between",
            "w-full",
            "py-2",
            "px-4",
            "rounded-lg",
            "cursor-pointer"
        );

        const div = document.createElement("div");
        div.classList.add("w-full", "text-lg", "font-semibold");
        div.textContent = title;

        label.appendChild(div);
        li.appendChild(input);
        li.appendChild(label);

        return li;
    }

    private pushError(message: string): void {
        console.error(message);
        Toastify({
            text: `Scan Libraries: ${message}`,
            backgroundColor: "#dc3545",
            duration: 3000,
            gravity: "bottom",
            position: "right",
            className: "toast",
            stopOnFocus: true,
        }).showToast();
    }
}

export default ScanLibraries;
