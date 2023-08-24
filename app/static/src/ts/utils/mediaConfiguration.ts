import axios from 'axios';
import cookie from 'js-cookie';
import toast from 'toastify-js';

import addToWindow from '../utils/addToWindow';
import { buttonSpinner } from './submitSpinner';

class MediaConfiguration {

    private axios = axios.create();

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

    // HTML divs for each input
    private input_div = {
        server_name: document.getElementById('server_name_div'),
        server_url: document.getElementById('server_url_div'),
        server_type: document.getElementById('server_type_div'),
        server_api: document.getElementById('server_api_key_div')
    };

    // HTML inputs for each div
    private input = {
        server_name: this.input_div.server_name?.querySelector('input'),
        server_url: this.input_div.server_url?.querySelector('input'),
        server_type: this.input_div.server_type?.querySelector('select'),
        server_api: this.input_div.server_api?.querySelector('input')
    };

    // HTML divs for each button
    private button_div = {
        scan_servers: document.getElementById('scan_servers_div'),
        scan_libraries: document.getElementById('scan_libraries_div'),
        test_connection: document.getElementById('test_connection_div'),
        save_configuration: document.getElementById('save_configuration_div')
    };

    // HTML buttons for each div
    private buttons = {
        scan_servers: this.button_div.scan_servers?.querySelector('button'),
        scan_libraries: this.button_div.scan_libraries?.querySelector('button'),
        test_connection: this.button_div.test_connection?.querySelector('button'),
        save_configuration: this.button_div.save_configuration?.querySelector('button')
    };

    // Detect server button and form if it exists
    private detect_server = document.getElementById('detect_server') as HTMLButtonElement | null | undefined;
    private form = this.buttons.save_configuration?.closest('form');
    private nav_btns = document.getElementById('navBtns');

    // Cached settings
    private cached_settings = {
        server_name: this.input_div.server_name?.getAttribute('data-default'),
        server_url: this.input_div.server_url?.getAttribute('data-default'),
        server_type: this.input_div.server_type?.getAttribute('data-default'),
        server_api: this.input_div.server_api?.getAttribute('data-default')
    }

    // Constructor for the MediaConfiguration class
    constructor(options: typeof MediaConfiguration.prototype) {
        // Initialise variables from options
        Object.assign(this, options);

        // Initialise the axios interceptor
        // @ts-ignore
        this.axios.defaults.headers.common["X-CSRF-TOKEN"] = cookie.get('csrf_access_token');
        this.axios.interceptors.response.use(this.resp.bind(this), this.error.bind(this));

        // Initialise the step based on the default values
        if (this.cached_settings.server_url && this.cached_settings.server_type && this.cached_settings.server_api) {
            this.steps[3].show();
        } else if (this.cached_settings.server_url) {
            this.steps[1].show();
        } else {
            this.steps[0].show();
        }

        // Add event listeners
        this.addEventListener(this.detect_server, 'click', this.detectServer.bind(this));
        this.addEventListener(this.buttons.test_connection, 'click', this.testConnection.bind(this));
        this.addEventListener(this.buttons.save_configuration, 'click', this.saveConfiguration.bind(this));

        // Add key listeners
        this.addKeyListener(this.input.server_url, 'Enter', this.detectServer.bind(this));
        this.addKeyListener(this.input.server_api, 'Enter', this.testConnection.bind(this));

        // Disable the form if it exists
        const form = this.buttons.save_configuration?.closest('form');
        this.disableForm(form);
    }

    // Different types of viewable elements depending on the step
    private steps = [
        {
            // Show Server Name and Server URL inputs
            // Show Scan Servers button
            inputs: [this.input_div.server_name, this.input_div.server_url],
            buttons: [this.button_div.scan_servers],
            show: () => this.show(0),
            hide: () => this.hide(0)
        },
        {
            // Show Server Name, Server URL, Server Type, and Server API inputs
            // Show Test Connection button
            inputs: [this.input_div.server_name, this.input_div.server_url, this.input_div.server_type, this.input_div.server_api],
            buttons: [this.button_div.test_connection],
            show: () => this.show(1),
            hide: () => this.hide(1)
        },
        {
            // Show Server Name, Server URL, Server Type, and Server API inputs
            // Show Scan Servers, Scan Libraries and Save Configuration buttons
            inputs: [this.input_div.server_name, this.input_div.server_url, this.input_div.server_type, this.input_div.server_api],
            buttons: [this.button_div.scan_servers, this.button_div.scan_libraries, this.button_div.save_configuration],
            show: () => this.show(2),
            hide: () => this.hide(2)
        },
        {
            // Show Server Name, Server URL, Server Type, and Server API inputs
            // Show Scan Libraries and Save Configuration buttons
            inputs: [this.input_div.server_name, this.input_div.server_url, this.input_div.server_type, this.input_div.server_api],
            buttons: [this.button_div.scan_servers, this.button_div.scan_libraries, this.button_div.save_configuration],
            show: () => this.show(3),
            hide: () => this.hide(3)
        },
        {
            // Show Server Name, Server URL, Server Type, and Server API inputs
            // Show Scan Libraries buttons
            inputs: [this.input_div.server_name, this.input_div.server_url, this.input_div.server_type, this.input_div.server_api],
            buttons: [this.button_div.scan_libraries],
            show: () => this.show(4),
            hide: () => this.hide(4)
        }
    ];

    // Show all elements for the current step and hide everything else
    private show(step: number) {
        // Input and Buttons for the current step
        const inputs = this.steps[step].inputs;
        const buttons = this.steps[step].buttons;

        // All input thats are in this.input_div but not in inputs
        const inputs_hide = Object.values(this.input_div).filter((element) => {
            return !inputs.includes(element);
        });

        // All buttons thats are in this.button_div but not in buttons
        const buttons_hide = Object.values(this.button_div).filter((element) => {
            return !buttons.includes(element);
        });

        // Merge the inputs and buttons arrays
        const merged = inputs.concat(buttons);
        const merged_hide = inputs_hide.concat(buttons_hide);

        merged.forEach((element) => {
            if (element?.classList.contains('hidden')) {
                element.classList.remove('hidden');
            }
        });

        merged_hide.forEach((element) => {
            if (!element?.classList.contains('hidden')) {
                element?.classList.add('hidden');
            }
        });
    }

    // Hide all elements for the current step and show everything else
    private hide(step: number) {
        // Input and Buttons for the current step
        const inputs = this.steps[step].inputs;
        const buttons = this.steps[step].buttons;

        // All input thats are in this.input_div but not in inputs
        const inputs_hide = Object.values(this.input_div).filter((element) => {
            return !inputs.includes(element);
        });

        // All buttons thats are in this.button_div but not in buttons
        const buttons_hide = Object.values(this.button_div).filter((element) => {
            return !buttons.includes(element);
        });

        // Merge the inputs and buttons arrays
        const merged = inputs.concat(buttons);
        const merged_hide = inputs_hide.concat(buttons_hide);

        merged.forEach((element) => {
            if (!element?.classList.contains('hidden')) {
                element?.classList.add('hidden');
            }
        });

        merged_hide.forEach((element) => {
            if (element?.classList.contains('hidden')) {
                element.classList.remove('hidden');
            }
        });
    }

    // Add event listener to an element with better error handling
    private addEventListener<K extends keyof HTMLElementEventMap>(html_element: HTMLInputElement | HTMLButtonElement | null | undefined, type: K, listener: EventListenerOrEventListenerObject | (() => Promise<void> | void)) {
        // Check if the html element is null
        if (html_element == null) {
            this.errorToast('Unable to add event listener');
            return;
        }

        // Debug message
        console.debug(`Adding event listener to ${html_element.id}`);

        // Add the event listener
        html_element.addEventListener(type, listener);
    }

    // Add key listener to an element with better error handling
    private addKeyListener(html_element: HTMLInputElement | null | undefined, key: string, callback: () => Promise<void> | void) {
        // Check if the html element is null
        if (html_element == null) {
            this.errorToast('Unable to add key listener');
            return;
        }

        // Debug message
        console.debug(`Adding key listener to ${html_element.id}`);

        // Add the event listener
        html_element.addEventListener('keydown', (event) => {
            // Change the type of event to KeyboardEvent
            const keyboard_event = event as KeyboardEvent | undefined;

            // If the key pressed was the enter key, then detect the server
            if (keyboard_event?.key === key) {
                keyboard_event.preventDefault();
                callback();
            }
        });
    }

    // Disable the form if it exists
    private disableForm(form: HTMLFormElement | null | undefined) {
        if (form == null) {
            this.errorToast('Unable to disable form');
            return;
        }

        form.onsubmit = (event) => event.preventDefault();
    }

    // Get the type of media server from the server URL
    private async getServerType(server_url: string): Promise<{ server_type: string, server_url: string }> {
        const resp = await this.axios.get('/api/utilities/detect-server', {
            params: {
                server_url
            }
        });

        if (resp.data == null || resp.status != 200) {
            throw new Error('Unable to detect server type');
        }

        return resp.data;
    }

    // Verify the server URL and API key
    private async verifyServer(server_url: string, api_key: string): Promise<string> {
        const resp = await this.axios.get('/api/utilities/verify-server', {
            params: {
                server_url,
                api_key
            }
        });

        if (resp.data == null || resp.status != 200) {
            throw new Error('Unable to verify server');
        }

        return resp.data;
    }

    // Validate a URL
    private urlValid(url: string): boolean {
        try {
            new URL(url);
            return true;
        } catch (error) {
            return false;
        }
    }

    // Detect the media server type
    public async detectServer() {
        // Start the loading spinner on the button
        buttonSpinner(this.detect_server as HTMLButtonElement, true);

        // Verify the server URL is valid using browser validation
        if (!this.input.server_url?.value || !this.urlValid(this.input.server_url.value)) {
            this.errorToast('Invalid server URL');
            buttonSpinner(this.detect_server as HTMLButtonElement, false);
            return;
        }

        // Detect the server type for the given URL
        const server_object = await this.getServerType(this.input.server_url.value).catch((error) => {
            this.errorToast(error.message ?? 'Unable to detect server type');
            return null;
        });

        // If the server type is null, then return
        if (server_object == null) {
            buttonSpinner(this.detect_server as HTMLButtonElement, false);
            return;
        }

        // Set the server type
        this.input.server_type?.querySelector(`option[value="${server_object.server_type}"]`)?.setAttribute('selected', 'selected');
        this.cached_settings.server_type = server_object.server_type;

        // Set the server URL
        this.input.server_url.value = server_object.server_url;
        this.cached_settings.server_url = server_object.server_url;

        // Clear the api key input
        if (this.input.server_api?.value) {
            this.input.server_api.value = '';
        }

        // Show the next step
        this.steps[1].show();
        this.input.server_api?.focus();

        // Stop the loading spinner on the button
        buttonSpinner(this.detect_server as HTMLButtonElement, false);
    }

    // Test the connection to the media server
    public async testConnection() {
        // Start the loading spinner on the button
        buttonSpinner(this.buttons.test_connection as HTMLButtonElement, true);

        // Verify the server URL is valid using browser validation
        if (!this.input.server_url?.value || !this.urlValid(this.input.server_url.value)) {
            this.errorToast('Invalid server URL');
            buttonSpinner(this.buttons.test_connection as HTMLButtonElement, false);
            return;
        }

        // Verify the server API key is valid using browser validation
        if (!this.input.server_api?.value) {
            this.errorToast('Invalid server API key');
            buttonSpinner(this.buttons.test_connection as HTMLButtonElement, false);
            return;
        }

        // Verify the server
        const server_name = await this.verifyServer(this.input.server_url.value, this.input.server_api.value).catch((error) => {
            this.errorToast(error.message ?? 'Unable to verify server');
            return null;
        });

        // If the server name is null, then return
        if (server_name == null) {
            buttonSpinner(this.buttons.test_connection as HTMLButtonElement, false);
            return;
        }

        // Save the configuration to the database
        await this.saveConfiguration();

        // Stop the loading spinner on the button
        buttonSpinner(this.buttons.test_connection as HTMLButtonElement, false);

        // If nav buttons exist, then show them
        if (this.nav_btns) {
            this.nav_btns.classList.remove('hidden');
            this.steps[4].show();
            return;
        }

        // Show the next step
        this.steps[2].show();
    }

    // Save the configuration to the database
    public async saveConfiguration() {
        // Validate the form using browser validation
        if (!this.form?.checkValidity()) {
            this.errorToast('Please fill out all required fields');
            return;
        }

        // Start the loading spinner on the button
        buttonSpinner(this.buttons.save_configuration as HTMLButtonElement, true);

        // Verify the server URL is valid using browser validation
        if (!this.input.server_url?.value || !this.urlValid(this.input.server_url.value)) {
            this.errorToast('Invalid server URL');
            buttonSpinner(this.buttons.save_configuration as HTMLButtonElement, false);
            return;
        }

        // Create a new FormData object from the form and save it to the database
        const data = new FormData(this.form);
        const resp = await this.axios.put('/api/settings', data).catch((error) => {
            this.errorToast(error.message ?? 'Unable to save configuration');
            return null;
        });

        // If the response status is not valid, then return
        if (resp == null || resp.status != 200) {
            buttonSpinner(this.buttons.save_configuration as HTMLButtonElement, false);
            this.errorToast('Unable to save configuration');
            return;
        }

        // Show a success toast
        this.infoToast('Successfully saved configuration');

        // Show the next step
        this.steps[3].show();

        // Stop the loading spinner on the button
        buttonSpinner(this.buttons.save_configuration as HTMLButtonElement, false);
    }

}

addToWindow(['utils', 'MediaConfiguration'], MediaConfiguration);