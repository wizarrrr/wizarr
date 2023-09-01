import axios from 'axios';
import cookie from 'js-cookie';
import toast from 'toastify-js';

import addToWindow from './addToWindow';
import { buttonSpinner } from './submitSpinner';

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
        tryAgainButton: document.getElementById('scan-servers-try-again') as HTMLButtonElement,
        subnet: null as string | null,
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
        if (resp?.data?.message) {
            this.infoToast(resp.data.message);
        }

        return resp;
    }

    // Initialise the axios interceptor
    error(error: any) {
        if (error?.response?.data?.message) {
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

        // Add the try again button event
        this.options.tryAgainButton.onclick = async (event) => {
            event.preventDefault();
            buttonSpinner(event.target as HTMLButtonElement, true);
            if (this.options.subnet) {
                this.infoToast('This may take a considerable amount of time, please be patient.');
                await this.scanAll(undefined, this.options.subnet);
                await this.build_gui();
            } else {
                this.errorToast('No subnet selected');
            }
            buttonSpinner(event.target as HTMLButtonElement, false);
        }

        // Scan all servers
        if (this.options.auto_scan) {
            this.scanAll();
        }
    }

    /**
     * Scan all the servers on the network
     * @returns List of servers
     */
    public async scanAll(ip?: string, subnet?: string): Promise<Array<any> | void> {
        // Get list of servers from the api
        const resp = await this.axios.get(this.options.api_endpoint, {
            params: {
                ip: ip,
                subnet: subnet
            }
        });

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

            const message = this.build_empty_message('No servers could be found.');
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

        // Add tiny text link "Don't see your server?"
        const tiny_text_div = document.createElement('div');
        tiny_text_div.classList.add('flex', 'flex-row', 'justify-start', 'items-start', 'text-xs', 'text-gray-900', 'dark:text-gray-400', 'mt-2', 'w-full');

        const tiny_text = document.createElement('a');
        tiny_text.classList.add('hover:text-primary', 'dark:hover:text-primary', 'transition', 'duration-150', 'ease-in-out');
        tiny_text.textContent = "Don't see your server?";

        tiny_text.onclick = () => {
            this.options.container.appendChild(this.build_empty_message('', true))
            tiny_text_div.remove();
        }

        tiny_text_div.appendChild(tiny_text);
        this.options.container.appendChild(tiny_text_div);
    }

    /**
     * Private method to build the individual server divs
     * @param server The server to build the div for
     * @returns The server div
     */
    private async build_server_div(server: Server): Promise<HTMLButtonElement> {
        // Hide the try again button
        this.options.tryAgainButton.classList.add('hidden');

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
    private build_empty_message(message: string, hide_message: boolean = false): HTMLDivElement {
        // Show the try again button
        this.options.tryAgainButton.classList.remove('hidden');
        this.options.tryAgainButton.disabled = true;

        // Create the message div
        const message_div = document.createElement('div');
        message_div.classList.add('flex', 'flex-col', 'items-center', 'space-y-4', 'text-gray-900', 'dark:text-white', 'mt-2');

        // Create the message content div
        const message_content_div = document.createElement('div');
        message_content_div.classList.add('flex', 'flex-col', 'items-center', 'space-y-2', 'text-gray-900', 'dark:text-white');

        // Create the message icon
        const message_icon = document.createElement('i');
        message_icon.classList.add('fas', 'fa-exclamation-triangle', 'fa-2x');

        // Create the message text
        const message_text = document.createElement('span');
        message_text.classList.add('text-sm', 'text-gray-900', 'dark:text-gray-400');
        message_text.textContent = message;

        // Create the subnet select div
        const subnet_select_div = document.createElement('div');
        subnet_select_div.classList.add('flex', 'flex-col', 'items-center', 'space-y-2', 'text-gray-900', 'dark:text-white', 'w-full');

        // Create the subnet select
        const subnet_select = document.createElement('select');
        subnet_select.id = 'subnet-select';
        subnet_select.classList.add('w-full', 'text-sm', 'rounded', 'border-gray-300', 'shadow-sm', 'focus:border-primary', 'focus:ring', 'focus:ring-primary', 'focus:ring-opacity-50', 'dark:bg-gray-700', 'dark:border-gray-600', 'dark:focus:border-gray-600', 'dark:focus:ring-gray-600', 'dark:focus:ring-opacity-50');

        // Create the subnet select options
        const subnet_select_options = [
            { value: '', text: 'Select your Media Servers subnet', disabled: true, selected: true },
            { value: '192.168.0.0/24', text: '192.168.0.0/24' },
            { value: '192.168.1.0/24', text: '192.168.1.0/24' },
            { value: '192.168.2.0/24', text: '192.168.2.0/24' },
            { value: '192.168.3.0/24', text: '192.168.3.0/24' },
            { value: '192.168.4.0/24', text: '192.168.4.0/24' },
            { value: '172.16.0.0/24', text: '172.16.0.0/24' },
            { value: '172.17.0.0/24', text: '172.17.0.0/24' },
            { value: '172.18.0.0/24', text: '172.18.0.0/24' },
            { value: '172.19.0.0/24', text: '172.19.0.0/24' },
            { value: '172.20.0.0/24', text: '172.20.0.0/24' },
            { value: '10.0.0.0/24', text: '10.0.0.0/24' },
            { value: '10.1.0.0/24', text: '10.1.0.0/24' },
            { value: '10.2.0.0/24', text: '10.2.0.0/24' },
            { value: '10.3.0.0/24', text: '10.3.0.0/24' },
            { value: '10.4.0.0/24', text: '10.4.0.0/24' },
        ];

        // Create the subnet select options
        for (const subnet_select_option of subnet_select_options) {
            const option = document.createElement('option');
            option.value = subnet_select_option.value;
            option.textContent = subnet_select_option.text;
            option.disabled = subnet_select_option.disabled ?? false;
            option.selected = subnet_select_option.selected ?? false;
            subnet_select.appendChild(option);
        }

        // Add the onchange event
        subnet_select.onchange = async () => {
            const subnet = subnet_select.value;
            this.options.subnet = subnet;
            this.options.tryAgainButton.disabled = false;
        }

        if (hide_message) {
            message_div.appendChild(subnet_select_div);
            subnet_select_div.appendChild(subnet_select);
            return message_div;
        }

        // Append elements to the message div
        message_div.appendChild(message_content_div);
        message_content_div.appendChild(message_icon);
        message_content_div.appendChild(message_text);
        message_div.appendChild(subnet_select_div);
        subnet_select_div.appendChild(subnet_select);


        return message_div;
    }

    /**
     * Retrive SVG logo from server
     * @returns The Logo as SVG
     */
    private async get_logo(logo: string): Promise<HTMLElement> {
        // Check if the logo is cached
        if (this.cachedLogos[logo]) {
            return this.cachedLogos[logo].cloneNode(true) as HTMLElement;
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
        this.cachedLogos[logo] = svg;

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