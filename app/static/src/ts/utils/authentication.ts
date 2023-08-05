import axios from 'axios';
import cookie from 'js-cookie';
import toast from 'toastify-js';

import {
    browserSupportsWebAuthn, browserSupportsWebAuthnAutofill, startAuthentication, startRegistration
} from '@simplewebauthn/browser';

import addToWindow from './addToWindow';

class Authentication {

    // Local axios instance
    axios = axios.create();

    // Store properties needed for the authentication class
    [key: string]: any;

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
            let auth = new Authentication([]);
            auth.infoToast(resp.data.message);
        }

        return resp;
    }

    // Initialise the axios interceptor
    error(error: any) {
        if (error.response.data.message) {
            let auth = new Authentication([]);
            auth.errorToast(error.response.data.message);
        }

        return Promise.reject(error);
    }

    /**
     * Create a new Authentication object
     * This class is used to login and logout the user and handle MFAs
     *
     * Login Parameters:
     * Used to login the user to the application
     *
     *  @param username: The username of the user
     *  @param password: The password of the user
     *  @param remember_me: Whether to remember the user or not
     *
     * Logout Parameters:
     * Used to logout the user from the application
     *
     * MFA Parameters:
     * Used to handle MFAs
     *
     * @returns An Authentication object
     */
    constructor(kwargs: object[]) {
        // Loop through the kwargs and set the properties
        for (const key in kwargs) {
            if (kwargs.hasOwnProperty(key)) {
                this[key] = kwargs[key];
            }
        }

        // @ts-ignore
        this.axios.defaults.headers.common["X-CSRF-TOKEN"] = cookie.get('csrf_access_token');
        this.axios.interceptors.response.use(this.resp, this.error);
    }

    /**
     * Login to the application
     * This method is used to login the user
     *
     * @param username The username of the user
     * @param password The password of the user
     * @param remember_me Optional parameter to remember the user, defaults to false
     *
     * @returns The response from the server
     */
    async login(username?: string, password?: string, remember_me?: boolean) {

        // Check if the username, password or remember_me are set
        if (username) this.username = username;
        if (password) this.password = password;
        if (remember_me) this.remember_me = remember_me;

        // Check that username, password are set
        if (!this.username || !this.password) {
            this.errorToast('Username or password not provided');
            throw new Error('Username or password not provided');
        }

        // Check if remember_me is set, if not set it to false
        if (!this.remember_me) {
            this.remember_me = false;
        }

        // Create a form data object
        const formData = new FormData();

        // Add the username, password and remember_me to the form data
        formData.append('username', this.username);
        formData.append('password', this.password);
        formData.append('remember', this.remember_me);

        // Send the request to the server
        const response = await this.axios.post('/api/auth/login', formData)

        // Check if the response is successful
        if (response.status != 200 || !response.data.auth) {
            this.errorToast(response.data.message || 'Failed to login, please try again');
            throw new Error('Failed to login, please try again');
        }

        // If auth has user object, set the user object to localStorage
        if (response.data.auth.user) {
            localStorage.setItem('user', JSON.stringify(response.data.auth.user));
        }

        // Redirect to the home page
        window.location.href = '/admin';
    }


    /**
     * Logout of the application
     * This method is used to logout the user
     *
     * @returns The response from the server
     */
    async logout() {

    }


    /**
     * Check MFA availability
     * This method is used to check if the user has MFA enabled
     *
     * @returns The boolean value of whether the user has MFA enabled
     */
    async isMFAEnabled(username?: string) {

        // Check if the username is set
        if (username) this.username = username;

        // Check if current device supports webauthn
        if (!browserSupportsWebAuthn()) {
            return false;
        }

        // Send the request to the server to check if the user has MFA enabled
        const response = await this.axios.post('/api/mfa/available', {
            username: this.username
        });

        // Check if the response is successful
        if (response.status != 200) {
            return false;
        }

        // Return the boolean value of whether the user has MFA enabled
        return response.data.mfa_available || false;
    }

    /**
     * Handle MFA registration
     * This method is used to handle MFA registration
     */
    async mfaRegistration() {

        // Make sure the browser supports webauthn
        if (!browserSupportsWebAuthn()) {
            this.errorToast('Your browser does not support WebAuthn');
            throw new Error('Your browser does not support WebAuthn');
        }

        // Fetch the registration options from the server
        const regResp = await this.axios.get('/api/mfa/registration');

        // Check if the response is successful
        if (regResp.status != 200) {
            this.errorToast(regResp.data.message || 'Failed to register, please try again');
            throw new Error('Failed to register, please try again');
        }

        // Get the registration options and delete the rp.id
        const registrationOptions = regResp.data;
        delete registrationOptions.rp.id;

        // Start the registration
        const registration = await startRegistration(regResp.data);

        // Data to send to the server
        const data = {
            "registration": JSON.stringify(registration),
            "origin": window.location.origin,
        };

        // Send the registration to the server
        const regResp2 = await this.axios.post('/api/mfa/registration', data);

        // Check if the response is successful
        if (regResp2.status != 200) {
            this.errorToast(regResp2.data.message || 'Failed to register, please try again');
            throw new Error('Failed to register, please try again');
        }

        // Return the response
        return regResp2;
    }


    /**
     * Handle MFA authentication
     * This method is used to handle MFA authentication
     *
     * @param username The username of the user
     */
    async mfaAuthentication(username?: string, autofill: boolean = false) {

        // Check if the username is set
        if (username) this.username = username;

        // Make sure the browser supports webauthn
        if (autofill && !browserSupportsWebAuthn()) {
            throw new Error('Your browser does not support WebAuthn');
        }

        // Make sure the browser supports webauthn autofill
        if (autofill && !browserSupportsWebAuthnAutofill()) {
            throw new Error('Your browser does not support WebAuthn Autofill');
        }

        // Check if the username is set
        if (!autofill && !this.username) {
            this.errorToast('Username not provided');
            throw new Error('Username not provided');
        }

        // Fetch the authentication options from the server
        const authResp = await this.axios.get('/api/mfa/authentication', {
            params: {
                username: this.username
            }
        });

        // Check if the response is successful
        if (authResp.status != 200) {
            this.errorToast(authResp.data.message || 'Failed to authenticate, please try again');
            throw new Error('Failed to authenticate, please try again');
        }

        // Get the authentication options
        const authenticationOptions = authResp.data;

        // Start the authentication
        const assertion = await startAuthentication(authenticationOptions, autofill);

        // Data to send to the server
        const data = {
            "assertion": JSON.stringify(assertion),
            "username": this.username,
            "origin": window.location.origin,
        };

        // Send the authentication to the server
        const authResp2 = await this.axios.post('/api/mfa/authentication', data);

        // Check if the response is successful
        if (authResp2.status != 200 || !authResp2.data.auth) {
            this.errorToast(authResp2.data.message || 'Failed to authenticate, please try again');
            throw new Error('Failed to authenticate, please try again');
        }

        // If auth has user object, set the user object to localStorage
        if (authResp2.data.auth.user) {
            localStorage.setItem('user', JSON.stringify(authResp2.data.auth.user));
        }

        // Redirect to the home page
        window.location.href = '/admin';
    }


    /**
     * MFA de-registration
     * This method is used to remove MFA from the user
     */
    async mfaDeregistration() {

        // Check if the username is set
        if (!this.username) {
            this.errorToast('Username not provided');
            throw new Error('Username not provided');
        }

        // Send the request to the server to remove MFA from the user
        const response = await this.axios.post('/api/mfa/deregistration', {
            username: this.username
        });

        // Check if the response is successful
        if (response.status != 200) {
            this.errorToast(response.data.message || 'Failed to deregister, please try again');
            throw new Error('Failed to deregister, please try again');
        }

        // Return the response
        return response;
    }

}

addToWindow(["utils", "Authentication"], Authentication);
