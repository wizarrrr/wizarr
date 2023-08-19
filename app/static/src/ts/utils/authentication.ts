import axios from 'axios';
import cookie from 'js-cookie';
import toast from 'toastify-js';

import { startAuthentication, startRegistration } from '@simplewebauthn/browser';

import addToWindow from './addToWindow';

import type { RegistrationResponseJSON } from '@simplewebauthn/typescript-types';
import type { WebAuthnError } from '@simplewebauthn/browser/dist/types/helpers/webAuthnError';

class Authentication {

    // Local axios instance
    private axios = axios.create();

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

    // Check if the browser supports webauthn
    browserSupportsWebAuthn() {
        return (window?.PublicKeyCredential !== undefined && typeof window.PublicKeyCredential === 'function');
    }

    // Check if the browser supports webauthn autofill
    async browserSupportsWebAuthnAutofill() {
        if (this.browserSupportsWebAuthn() === false) {
            return false;
        }

        if (typeof window.PublicKeyCredential.isConditionalMediationAvailable !== 'function') {
            return false;
        }

        return (await window.PublicKeyCredential.isConditionalMediationAvailable() === true);
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
    constructor(kwargs: object[] = []) {
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
     * Redirect user to the authenticated page
     * This function is used to redirect the user to the authenticated page
     */
    redirect(path?: string, toast?: string) {
        // Get redirect param from the url
        const urlParams = new URLSearchParams(window.location.search);
        let redirect = urlParams.get('redirect');

        // If the redirect param is set, make sure its a pathname
        if (redirect && !redirect.startsWith('/')) redirect = null;

        // Create path to redirect to
        const newPath = new URL(window.location.origin + (redirect || path || '/admin'));

        // Add a toast notification to welcome the user
        newPath.searchParams.append('toast', toast || 'Welcome back ' + this.username);

        // Redirect to the home page or the redirect param if it exists
        window.location.href = newPath.href;
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
            console.error('Username or password not provided');
            return;
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
            console.error(response.data.message || 'Failed to login, please try again');
            return;
        }

        // If auth has user object, set the user object to localStorage
        if (response.data.auth.user) {
            localStorage.setItem('user', JSON.stringify(response.data.auth.user));
        }

        // If auth has token object, set the token object to localStorage
        if (response.data.auth.token) {
            // Set the token to the access_token_cookie
            cookie.set('access_token_cookie', response.data.auth.token.access_token);
        }

        // Redirect the user to the authenticated page
        this.redirect();
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
        if (!this.browserSupportsWebAuthn()) {
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
    async mfaRegistration(mfaName?: string) {

        // Check if the mfaName is set
        if (mfaName) this.mfaName = mfaName;

        // Make sure the browser supports webauthn
        if (!this.browserSupportsWebAuthn()) {
            this.errorToast('Your browser does not support WebAuthn');
            console.error('Your browser does not support WebAuthn');
            return;
        }

        // Fetch the registration options from the server
        const regResp = await this.axios.get('/api/mfa/registration');

        // Check if the response is successful
        if (regResp.status != 200) {
            this.errorToast(regResp.data.message || 'Failed to register, please try again');
            console.error(regResp.data.message || 'Failed to register, please try again');
            return;
        }

        // Get the registration options and delete the rp.id
        const registrationOptions = regResp.data;
        delete registrationOptions.rp.id;

        // Create a new registration object
        let registration: RegistrationResponseJSON

        // Start the registration
        try {
            registration = await startRegistration(regResp.data);
        } catch (e: any) {
            this.errorToast((e as WebAuthnError).message || 'Failed to register, please try again');
            console.error((e as WebAuthnError).message || 'Failed to register, please try again');
            return;
        }

        // Data to send to the server
        const data = {
            "registration": JSON.stringify(registration),
            "origin": window.location.origin,
            "name": this.mfaName
        };

        // Send the registration to the server
        const regResp2 = await this.axios.post('/api/mfa/registration', data);

        // Check if the response is successful
        if (regResp2.status != 200) {
            this.errorToast(regResp2.data.message || 'Failed to register, please try again');
            console.error(regResp2.data.message || 'Failed to register, please try again');
            return;
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
        if (!this.browserSupportsWebAuthn()) {
            console.error('Your browser does not support WebAuthn');
            return;
        }

        // Make sure the browser supports webauthn autofill
        if (autofill && !(await this.browserSupportsWebAuthnAutofill())) {
            console.error('Your browser does not support WebAuthn Autofill');
            return;
        }

        // Check if the username is set
        if (!autofill && !this.username) {
            this.errorToast('Username not provided');
            console.error('Username not provided');
            return;
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
            console.error(authResp.data.message || 'Failed to authenticate, please try again');
            return;
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
            console.error(authResp2.data.message || 'Failed to authenticate, please try again');
            return;
        }

        // If auth has user object, set the user object to localStorage
        if (authResp2.data.auth.user) {
            localStorage.setItem('user', JSON.stringify(authResp2.data.auth.user));
        }

        // Redirect the user to the authenticated page
        this.redirect();
    }


    /**
     * MFA de-registration
     * This method is used to remove MFA from the user
     */
    async mfaDeregistration() {

        // Check if the username is set
        if (!this.username) {
            this.errorToast('Username not provided');
            console.error('Username not provided');
            return;
        }

        // Send the request to the server to remove MFA from the user
        const response = await this.axios.post('/api/mfa/deregistration', {
            username: this.username
        });

        // Check if the response is successful
        if (response.status != 200) {
            this.errorToast(response.data.message || 'Failed to deregister, please try again');
            console.error(response.data.message || 'Failed to deregister, please try again');
            return;
        }

        // Return the response
        return response;
    }

}

addToWindow(["utils", "Authentication"], Authentication);

export default Authentication;