import axios from 'axios';
import cookie from 'js-cookie';
import toast from 'toastify-js';

import addToWindow from './addToWindow';

declare type Server = {
    host: string;
    port: number;
    server_type: 'jellyfin' | 'plex';
};

declare type Servers = Array<Server>;

class ScanServers {

    // Local axios instance and other variables
    private axios = axios.create();
    private cachedLogos: Record<string, HTMLElement> = {};
    private options = {
        container: document.getElementById('scan-servers') as HTMLElement,
        api_endpoint: '/api/utilities/scan-servers',
        auto_scan: false,
        callback: (server: Server) => { console.error('No callback set for scan servers', server) },
    }

    public servers: Servers = [];

    // Local toast config
    defaultToast: Toastify.Options = {
        duration: 3000,
        gravity: 'bottom',
        position: 'right',
        className: 'toast',
        stopOnFocus: true
    };

    // Normal toast notifications
    infoToast = (message: string) => {
        toast({
            text: message,
            style: {
                background: '#4B5563',
            },
            ...this.defaultToast,
        }).showToast();
    }

    // Error toast notifications
    errorToast = (message: string) => {
        toast({
            text: message,
            style: {
                background: '#dc3545',
            },
            ...this.defaultToast,
        }).showToast();
    }

    // Initialise the axios interceptor
    resp<V>(resp: any) {
        if (resp.data.message) {
            this.infoToast(resp.data.message);
        }

        return resp;
    }

    // Initialise the axios interceptor
    error(error: any) {
        if (error.response.data.message) {
            this.errorToast(error.response.data.message);
        }

        return Promise.reject(error);
    }

    /**
     * Initialise the scan servers class
     * This class is used to scan all the servers on the network and provide a list of them
     *
     * @param container The container to use for the scan servers
     * @returns void
     */
    constructor(options?: Partial<typeof ScanServers.prototype.options>) {
        // Merge the options
        if (options) {
            this.options = { ...this.options, ...options };
        }

        // @ts-ignore
        this.axios.defaults.headers.common["X-CSRF-TOKEN"] = cookie.get('csrf_access_token');
        this.axios.interceptors.response.use(this.resp.bind(this), this.error.bind(this));

        console.log(this.options.container)

        // Scan all servers
        if (this.options.auto_scan) {
            this.scanAll();
        }
    }

    /**
     * Scan all the servers on the network
     * @returns List of servers
     */
    public async scanAll(): Promise<Array<any> | void> {
        // Get list of servers from the api
        const resp = await this.axios.get(this.options.api_endpoint);

        // If the response is not ok, return
        if (resp.status !== 200) {
            this.errorToast('Failed to scan servers');
            return;
        }

        // If the response is ok, check that the data is an array
        if (!Array.isArray(resp.data)) {
            this.errorToast('Failed to scan servers');
            return;
        }

        // If the response is ok and the data is an array, set the servers
        this.servers = resp.data as Servers;
        return resp.data;
    }

    /**
     * Build the GUI for the server list
     */
    public async build_gui() {
        // Check that the container exists
        if (!this.options.container) {
            this.errorToast('Failed to build GUI');
            return;
        }

        // Clear the container
        this.options.container.innerHTML = '';

        // Check that the servers are not empty
        if (this.servers.length === 0) {
            this.errorToast('No servers found');

            const message = this.build_empty_message('No servers found');
            this.options.container.appendChild(message);

            return;
        }

        // Make sure container has these classes
        this.options.container.classList.add('flex', 'flex-col', 'gap-1');

        // Build the GUI
        for (const server of this.servers) {
            const server_div = await this.build_server_div(server);
            this.options.container.appendChild(server_div);
        }

    }

    /**
     * Private method to build the individual server divs
     * @param server The server to build the div for
     * @returns The server div
     */
    private async build_server_div(server: Server): Promise<HTMLButtonElement> {
        // Create the server div
        const server_button = document.createElement('button');
        server_button.classList.add(
            'relative',
            'bg-white',
            'rounded',
            'shadow-md',
            'dark:bg-gray-800',
            'dark:border',
            'dark:border-gray-700',
            'overflow-hidden',
            'hover:bg-gray-50',
            'dark:hover:bg-gray-700',
            'cursor-pointer',
            'group',
            'transition',
            'duration-150',
            'ease-in-out'
        );

        // Add the onclick event
        server_button.onclick = () => {
            this.options.callback(server);
        }

        // Create the server div content
        const server_div_content = document.createElement('div');
        server_div_content.classList.add(
            'flex',
            'flex-row',
            'justify-start',
            'p-3',
            'items-center'
        );

        // Create the server icon div
        const server_icon_div = document.createElement('div');
        server_icon_div.classList.add(
            'aspect-square',
            'h-full',
            'p-3',
            'bg-gray-100',
            'rounded',
            'flex',
            'items-center',
            'justify-center',
            'bg-gray-100',
            'dark:bg-gray-700',
            'group-hover:bg-gray-200',
            'dark:group-hover:bg-gray-600',
            'transition',
            'duration-150',
            'ease-in-out'
        );

        // Create the server icon using SVG
        const server_icon = await this.get_logo(server.server_type);
        server_icon.classList.add(
            'w-6',
            'h-6',
            'fill-gray-500',
            'dark:fill-gray-400',
            'transition',
            'duration-150',
            'ease-in-out'
        );

        // Create the server info div
        const server_info_div = document.createElement('div');
        server_info_div.classList.add('flex', 'flex-col', 'ml-4');

        // Create the server title div
        const server_title_div = document.createElement('div');
        server_title_div.textContent = this.server_type_to_string(server.server_type);
        server_title_div.classList.add('text-sm', 'font-bold', 'text-start', 'leading-tight', 'tracking-tight', 'text-gray-900', 'md:text-md', 'dark:text-gray-400', 'line-clamp-1');

        // Create the server description div
        const server_description_div = document.createElement('div');
        server_description_div.classList.add('text-xs', 'text-start', 'leading-tight', 'tracking-tight', 'text-gray-900', 'md:text-sm', 'dark:text-gray-400', 'line-clamp-1');

        // Create a URL from host and port
        const server_url = new URL(`http://${server.host}:${server.port}`);
        server_description_div.textContent = server_url.toString();

        // Append elements to the server div
        server_button.appendChild(server_div_content);
        server_div_content.appendChild(server_icon_div);
        server_icon_div.appendChild(server_icon);
        server_div_content.appendChild(server_info_div);
        server_info_div.appendChild(server_title_div);
        server_info_div.appendChild(server_description_div);

        return server_button;
    }

    /**
     * Private method to build a message for empty list
     * @returns The message div
     */
    private build_empty_message(message: string): HTMLDivElement {
        return document.createElement('div');
    }

    /**
     * Retrive SVG logo from server
     * @returns The Logo as SVG
     */
    private async get_logo(logo: string): Promise<HTMLElement> {
        // Check if the logo is cached
        if (this.cachedLogos[logo]) {
            return this.cachedLogos[logo];
        }

        // Import SVG from axios request
        const request = await this.axios.get('/static/img/logo/' + logo + '.svg');

        // Verify the request was successful
        if (request.status !== 200) {
            const icon = document.createElement('i');
            icon.classList.add('fas', 'fa-question-circle');
            return icon;
        }

        // Parse the SVG to HTML
        const parser = new DOMParser();
        const svg = parser.parseFromString(request.data as string, 'image/svg+xml').documentElement;

        // Cache the logo HTML as a copy
        this.cachedLogos[logo] = svg.cloneNode(true) as HTMLElement;

        // Return the logo
        return svg;
    }

    /**
     * Private method to convert server type to string
     * @param server_type The server type to convert
     * @returns The server type as a string
     */
    private server_type_to_string(server_type: typeof ScanServers.prototype.servers[0]['server_type']): string {
        switch (server_type) {
            case 'jellyfin':
                return 'Jellyfin Server';
            case 'plex':
                return 'Plex Server';
            default:
                return 'Unknown Server';
        }
    }
}

addToWindow(['utils', 'ScanServers'], ScanServers);
export default ScanServers;