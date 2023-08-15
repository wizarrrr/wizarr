import axios from 'axios';
import cookie from 'js-cookie';
import toast from 'toastify-js';

import addToWindow from '../utils/addToWindow';

interface NotificationResources extends Array<NotificationResource> { }

interface NotificationResource {
    name: string;
    class: string;
    resource: Resource[];
}

export interface Resource {
    name: string;
    metadata: Metadata;
    default?: number | string;
    type: Type;
    required?: boolean;
}

export interface Metadata {
    name?: string;
    icon?: string;
    description?: string;
    type?: string;
}

export enum Type {
    Bool = "bool",
    Int = "int",
    Str = "str",
}

class Notifications {

    // Local axios instance
    private axios = axios.create();
    private resources: NotificationResources = [];

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
            const notifications = new Notifications();
            notifications.infoToast(resp.data.message);
        }

        return resp;
    }

    // Initialise the axios interceptor
    error(error: any) {
        if (error.response.data.message) {
            const notifications = new Notifications();
            notifications.errorToast(error.response.data.message);
        }

        return Promise.reject(error);
    }

    /**
     * Constructor for the Notifications class
     * This class is used build the GUI for creating and editing notifications
     */
    constructor() {
        // @ts-ignore
        this.axios.defaults.headers.common["X-CSRF-TOKEN"] = cookie.get('csrf_access_token');
        this.axios.interceptors.response.use(this.resp, this.error);
    }

    /**
     * Public method to build the GUI for creating a notification
     * @param container The container to build the GUI in
     */
    public async build_gui(container: HTMLElement): Promise<void> {
        // Get the notification resources
        await this.get_resources();

        // Create a form for the notification
        const form = document.createElement('form');
        form.classList.add('space-y-4', 'md:space-y-6');

        // Create a label and input for the name of the notification
        const name = this.build_generic_label_input('name', 'Name', 'e.g. "My Agent"', Type.Str, true);

        // Create the select element for the notification resources
        const select = this.build_generic_label_select('type', 'Notification Service', this.resources);

        // Create a container that will hold the inputs for the notification resource
        const resource_container = document.createElement('div');
        resource_container.id = 'resource_container';
        resource_container.classList.add('space-y-4', 'md:space-y-6');

        // Create a button to submit the form and cancel the modal
        const submit = document.createElement('button');
        submit.type = 'submit';
        submit.className = 'inline-flex w-full justify-center rounded bg-primary px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary_hover sm:ml-3 sm:w-auto';
        submit.innerText = 'Test & Create Agent';

        // Create a button to cancel the modal
        const cancel = document.createElement('button');
        cancel.type = 'button';
        cancel.className = 'inline-flex w-full justify-center rounded bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto';
        cancel.innerText = 'Cancel';
        cancel.onclick = () => {
            // @ts-ignore
            window.utils.closeModal(cancel);
        }

        // Create a container for the buttons
        const button_container = document.createElement('div');
        button_container.className = 'flex justify-end pt-2 space-x-4';

        // Add the buttons to the button container
        button_container.appendChild(cancel);
        button_container.appendChild(submit);

        // Join everything together
        form.appendChild(name);
        form.appendChild(select);
        form.appendChild(resource_container);
        form.appendChild(button_container);

        container.replaceChildren(form);
    }

    /**
     * Private method to get the resources from the API
     */
    private async get_resources(): Promise<NotificationResources> {
        const resp = await this.axios.get('/api/notifications/resources');
        this.resources = resp.data;

        return resp.data;
    }

    /**
     * Private method to build a select element for the notification resources
     * @param names An array of the names of the notification resources
     *
     * @returns A select element for the notification resources
     */
    private build_resource_select(resources: NotificationResources): HTMLSelectElement {
        const select = document.createElement('select');
        select.name = 'type';
        select.id = 'type';
        select.className = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded focus:ring-primary focus:border-primary block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white';
        select.onchange = this.build_resource_inputs.bind(this);
        select.required = true;

        const option = document.createElement('option');
        option.selected = true;
        option.disabled = true;
        option.text = 'Choose a service';
        select.appendChild(option);

        for (const resource of resources) {
            const option = document.createElement('option');
            option.value = resource.class;
            option.text = resource.name;
            select.appendChild(option);
        }

        return select;
    }

    /**
     * Private method to build resource inputs when select is changed
     * @param event The event that triggered the change
     */
    private build_resource_inputs(event: Event): void {
        // Get the selected resource from the event
        const select = event.target as HTMLSelectElement;
        const selected = select.options[select.selectedIndex].value;

        // Get the resource from the resources
        const resource = this.resources.find(resource => resource.class === selected) as NotificationResource;

        // If the resource is not found, return
        if (!resource) {
            throw new Error('Resource not found for selected value: ' + selected);
        }

        // Get the resource container
        const resource_container = document.getElementById('resource_container') as HTMLDivElement;

        // Clear the resource container
        resource_container.replaceChildren();

        // Build the inputs for the resource
        for (const item of resource.resource) {

            // Skip the first item, as it is the name of the resource
            if (resource.name === item.name) {
                continue;
            }

            const input = this.build_resource_label_input(item);
            resource_container.appendChild(input);
        }

    }

    /**
     * Private method to build a input element for the notification resources
     * @param item The notification resource item
     *
     * @returns An input element for the notification resources
     */
    private build_resource_input(item: Resource): HTMLInputElement {
        return this.build_generic_input(item.name || '', item.metadata.description || '', item.metadata.type || item.type, item.required || false, item.default as string || '');
    }

    /**
     * Private method to build a resource label, input combination
     * @param item The notification resource item
     *
     * @returns A label, input combination
     */
    private build_resource_label_input(item: Resource): HTMLDivElement {
        const div = document.createElement('div');
        div.className = 'flex flex-' + (item.metadata.type === 'checkbox' || item.type === Type.Bool ? 'row-reverse' : 'col');

        if (item.metadata.type === 'checkbox' || item.type === Type.Bool) {
            div.classList.add('justify-end', 'gap-2');
        }

        const label = this.build_generic_label(item.name || '', item.metadata.name || '');
        const input = this.build_resource_input(item);

        div.appendChild(label);
        div.appendChild(input);

        return div;
    }

    /**
     * Private method to build a generic label, input combination
     * @param name The name of the label and input element
     * @param text The text of the label element
     * @param placeholder The placeholder of the input element
     * @param required Whether the input element is required
     * @param value The value of the input element
     *
     * @returns A label, input combination
     */
    private build_generic_label_input(name: string, text: string, placeholder: string, type: Type | string = Type.Str, required: boolean = true, value: string = ''): HTMLDivElement {
        const div = document.createElement('div');
        div.className = 'flex flex-' + (type === 'checkbox' || type === Type.Bool ? 'row-reverse' : 'col');

        if (type === 'checkbox' || type === Type.Bool) {
            div.classList.add('justify-end', 'gap-2');
        }

        const label = this.build_generic_label(name, text);
        const input = this.build_generic_input(name, placeholder, type, required, value);

        div.appendChild(label);
        div.appendChild(input);

        return div;
    }

    /**
     * Private method to build a generic label, select combination
     * @param name The name of the label and input element
     * @param text The text of the label element
     * @param placeholder The placeholder of the input element
     * @param required Whether the input element is required
     * @param value The value of the input element
     *
     * @returns A label, input combination
     */
    private build_generic_label_select(name: string, text: string, resource: NotificationResources): HTMLDivElement {
        const div = document.createElement('div');
        div.className = 'flex flex-col';

        const label = this.build_generic_label(name, text);
        const select = this.build_resource_select(resource);

        div.appendChild(label);
        div.appendChild(select);

        return div;
    }

    /**
    * Private method to build a generic input element
    * @param name The name of the input element
    * @param placeholder The placeholder of the input element
    * @param required Whether the input element is required
    * @param value The value of the input element
    *
    * @returns An input element
    */
    private build_generic_input(name: string, placeholder: string, type: Type | string = Type.Str, required: boolean = true, value: string = ''): HTMLInputElement {
        const input = document.createElement('input');
        input.type = this.convert_type(type);
        input.name = name;
        input.id = name;
        input.className = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded focus:ring-primary focus:border-primary block p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white';
        input.placeholder = placeholder;
        input.required = required;
        input.value = value;
        input.autocomplete = 'one-time-code';

        if (type !== Type.Bool && type !== 'checkbox') {
            input.classList.add('w-full');
        }

        return input;
    }

    /**
     * Private method to build a generic label element
     * @param name The name of the label element
     * @param text The text of the label element
     *
     * @returns A label element
     */
    private build_generic_label(name: string, text: string): HTMLLabelElement {
        const label = document.createElement('label');
        label.htmlFor = name;
        label.className = 'block mb-2 text-sm font-medium text-gray-900 dark:text-white';
        label.innerText = text;

        return label;
    }

    /**
     * Private method to convert a python type to a javascript type
     * @param type The python type
     *
     * @returns The javascript type
     */
    private convert_type(type: Type | string): string {
        switch (type) {
            case Type.Str:
                return 'text';
            case Type.Int:
                return 'number';
            case Type.Bool:
                return 'checkbox';
            default:
                return type;
        }
    }

}

addToWindow(['utils', 'Notifications'], Notifications);

export default Notifications;