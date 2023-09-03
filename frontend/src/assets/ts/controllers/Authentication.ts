import axios from "../utils/Axios";

import { startAuthentication, startRegistration } from "@simplewebauthn/browser";
import { infoToast, errorToast } from "../utils/Toasts";
import { useRouter } from "vue-router";

import type { RegistrationResponseJSON } from "@simplewebauthn/typescript-types";
import type { WebAuthnError } from "@simplewebauthn/browser/dist/types/helpers/webAuthnError";
import type { APIUser } from "@/types/User";

class Authentication {
    // Local axios instance
    private axios = axios;

    // Local toast functions
    private errorToast = errorToast;
    private infoToast = infoToast;

    // Router instance
    private router = useRouter();

    // Store properties needed for the authentication class
    [key: string]: any;

    // Check if the browser supports webauthn
    browserSupportsWebAuthn() {
        return window?.PublicKeyCredential !== undefined && typeof window.PublicKeyCredential === "function";
    }

    // Check if the browser supports webauthn autofill
    async browserSupportsWebAuthnAutofill() {
        if (this.browserSupportsWebAuthn() === false) {
            return false;
        }

        if (typeof window.PublicKeyCredential.isConditionalMediationAvailable !== "function") {
            return false;
        }

        return (await window.PublicKeyCredential.isConditionalMediationAvailable()) === true;
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

        this.axios.disableInfoToast = true;
    }

    /**
     * Handle Authenticated Data
     * This function is used to handle authenticated data to store
     */
    handleAuthData(user: Partial<APIUser>, token: string) {
        // Redirect the user to the home page
        this.router.push("/admin");

        // Show a welcome message to the display_name else username
        infoToast(`Welcome ${user.display_name || user.username}`);

        // Reset the user data
        return { user, token };
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
            this.errorToast("Username or password not provided");
            console.error("Username or password not provided");
            return;
        }

        // Check if remember_me is set, if not set it to false
        if (!this.remember_me) {
            this.remember_me = false;
        }

        // Create a form data object
        const formData = new FormData();

        // Add the username, password and remember_me to the form data
        formData.append("username", this.username);
        formData.append("password", this.password);
        formData.append("remember", this.remember_me);

        // Send the request to the server
        const response = await this.axios.post("/api/auth/login", formData);

        // Check if the response is successful
        if (response.status != 200 || !response.data.auth) {
            this.errorToast(response.data.message || "Failed to login, please try again");
            console.error(response.data.message || "Failed to login, please try again");
            return;
        }

        // Handle the authenticated data
        return this.handleAuthData(response.data.auth.user, response.data.auth.token);
    }

    /**
     * Logout of the application
     * This method is used to logout the user
     *
     * @returns The response from the server
     */
    async logout() {}

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
        const response = await this.axios.post("/api/mfa/available", {
            username: this.username,
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
            this.errorToast("Your browser does not support WebAuthn");
            console.error("Your browser does not support WebAuthn");
            return;
        }

        // Fetch the registration options from the server
        const regResp = await this.axios.get("/api/mfa/registration");

        // Check if the response is successful
        if (regResp.status != 200) {
            this.errorToast(regResp.data.message || "Failed to register, please try again");
            console.error(regResp.data.message || "Failed to register, please try again");
            return;
        }

        // Get the registration options and delete the rp.id
        const registrationOptions = regResp.data;
        delete registrationOptions.rp.id;

        // Create a new registration object
        let registration: RegistrationResponseJSON;

        // Start the registration
        try {
            registration = await startRegistration(regResp.data);
        } catch (e: any) {
            this.errorToast((e as WebAuthnError).message || "Failed to register, please try again");
            console.error((e as WebAuthnError).message || "Failed to register, please try again");
            return;
        }

        // Data to send to the server
        const data = {
            registration: JSON.stringify(registration),
            origin: window.location.origin,
            name: this.mfaName,
        };

        // Send the registration to the server
        const regResp2 = await this.axios.post("/api/mfa/registration", data);

        // Check if the response is successful
        if (regResp2.status != 200) {
            this.errorToast(regResp2.data.message || "Failed to register, please try again");
            console.error(regResp2.data.message || "Failed to register, please try again");
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
            console.error("Your browser does not support WebAuthn");
            return;
        }

        // Make sure the browser supports webauthn autofill
        if (autofill && !(await this.browserSupportsWebAuthnAutofill())) {
            console.error("Your browser does not support WebAuthn Autofill");
            return;
        }

        // Check if the username is set
        if (!autofill && !this.username) {
            this.errorToast("Username not provided");
            console.error("Username not provided");
            return;
        }

        // Fetch the authentication options from the server
        const authResp = await this.axios.get("/api/mfa/authentication", {
            params: {
                username: this.username,
            },
        });

        // Check if the response is successful
        if (authResp.status != 200) {
            this.errorToast(authResp.data.message || "Failed to authenticate, please try again");
            console.error(authResp.data.message || "Failed to authenticate, please try again");
            return;
        }

        // Get the authentication options
        const authenticationOptions = authResp.data;

        // Start the authentication
        const assertion = await startAuthentication(authenticationOptions, autofill).catch((e: any) => {
            return null;
        });

        // Check if the assertion is null
        if (!assertion) return;

        // Data to send to the server
        const data = {
            assertion: JSON.stringify(assertion),
            username: this.username,
            origin: window.location.origin,
        };

        // Send the authentication to the server
        const authResp2 = await this.axios.post("/api/mfa/authentication", data).catch((e: any) => {
            this.errorToast(e.data.message || "Failed to authenticate, please try again");
            return null;
        });

        // Check if the response is null
        if (!authResp2) return;

        // Handle the authenticated data
        return this.handleAuthData(authResp2.data.auth.user, authResp2.data.auth.token);
    }

    /**
     * MFA de-registration
     * This method is used to remove MFA from the user
     */
    async mfaDeregistration() {
        // Check if the username is set
        if (!this.username) {
            this.errorToast("Username not provided");
            console.error("Username not provided");
            return;
        }

        // Send the request to the server to remove MFA from the user
        const response = await this.axios.post("/api/mfa/deregistration", {
            username: this.username,
        });

        // Check if the response is successful
        if (response.status != 200) {
            this.errorToast(response.data.message || "Failed to deregister, please try again");
            console.error(response.data.message || "Failed to deregister, please try again");
            return;
        }

        // Return the response
        return response;
    }
}

export default Authentication;
