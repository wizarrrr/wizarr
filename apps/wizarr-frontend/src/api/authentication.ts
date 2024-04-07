import { errorToast, infoToast, successToast } from "../ts/utils/toasts";
import { startAuthentication, startRegistration } from "@simplewebauthn/browser";

import type { APIUser } from "@/types/api/auth/User";
import type { RegistrationResponseJSON } from "@simplewebauthn/typescript-types";
import type { WebAuthnError } from "@simplewebauthn/browser/dist/types/helpers/webAuthnError";
import { useAuthStore } from "@/stores/auth";
import { useAxios } from "@/plugins/axios";
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";

class Auth {
    // Local toast functions
    private errorToast = errorToast;
    private infoToast = infoToast;
    private successToast = successToast;

    // Router and axios instance
    private router = useRouter();
    private axios = useAxios();

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
     * @returns An Authentication object
     */
    constructor() {
        this.axios.disableInfoToast = true;
    }

    /**
     * Handle Authenticated Data
     * This function is used to handle authenticated data to store
     */
    async handleAuthData(user: Partial<APIUser>, token: string, refresh_token: string) {
        // Get auth store from pinia
        const authStore = useAuthStore();
        const userStore = useUserStore();

        // Redirect the user to the home page
        this.router.push("/admin");

        // Show a welcome message to the display_name else username
        this.infoToast(`Welcome ${user.display_name ?? user.username}`);

        // Set the user data
        userStore.setUser(user);

        // Set the auth token and refresh token
        authStore.setAccessToken(token);
        authStore.setRefreshToken(refresh_token);

        // Reset the user data
        return { user, token };
    }

    /**
     * Get the current user
     * This method is used to get the current user
     */
    async getCurrentUser() {
        // Send the request to the server to get the current user
        const response = await this.axios.get("/api/auth/me");

        // Check if the response is successful
        if (response.status != 200) {
            this.errorToast(response.data.message || "Failed to get current user, please try again");
            console.error(response.data.message || "Failed to get current user, please try again");
            return;
        }

        // Return the response
        return response.data.user;
    }

    /**
     * Check if the user is authenticated
     * This method is used to check if the user is authenticated
     */
    async isAuthenticated() {
        // Get auth store from pinia
        const authStore = useAuthStore();

        // Check if the JWT token is expired
        if (!authStore.isAccessTokenExpired()) {
            return true;
        }

        // Refresh the JWT token
        return await this.refreshToken().catch(() => false);
    }

    /**
     * Refresh the JWT token
     * This method is used to refresh the JWT token
     */
    async refreshToken() {
        // Get auth store from pinia
        const authStore = useAuthStore();

        // Check if the access token and refresh token are set
        if (!authStore.token || !authStore.refresh_token) {
            return false;
        }

        // Send the request to the server to refresh the JWT token
        const response = await this.axios.post("/api/auth/refresh", undefined, {
            refresh_header: true,
            disableErrorToast: true,
        });

        // Check if the response is null
        if (!response || response.status != 200) {
            this.errorToast("Failed to refresh token, please login again.");
            return false;
        }

        // Set the new JWT token
        authStore.setAccessToken(response.data.access_token);

        // Return the response
        return true;
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
        return this.handleAuthData(response.data.auth.user, response.data.auth.token, response.data.auth.refresh_token);
    }

    /**
     * Change Password
     * This method is change the password of the user
     *
     * @param old_password The old password of the user
     * @param new_password The new password of the user
     *
     * @returns The response from the server
     */
    async changePassword(old_password?: string, new_password?: string) {
        const userStore = useUserStore();

        // verify if the user is authenticated
        if (!this.isAuthenticated()) {
            this.errorToast("User is not authenticated");
            return;
        }

        // check if old assword is correct
        const username = userStore.user?.username;

        if (old_password) this.old_password = old_password;
        if (new_password) this.new_password = new_password;
        if (username) this.username = username;

        // Create a form data object
        const formData = new FormData();

        // Add the username, password and remember_me to the form data
        formData.append("old_password", this.old_password);
        formData.append("new_password", this.new_password);
        formData.append("username", this.username);

        // send request to server to change password
        await this.axios
            .post("/api/accounts/change_password", formData)
            .then((res) => {
                this.successToast("Password changed successfully");
                this.infoToast("Logging out in 5 seconds...");
                setTimeout(() => {
                    this.logout();
                }, 5000);
                return res;
            })
            .catch(() => {
                this.errorToast("Failed to change password, please try again");
                return;
            });
    }

    /**
     * Logout of the application
     * This method is used to logout the user
     *
     * @returns The response from the server
     */
    async logout() {
        // Get auth store from pinia
        const authStore = useAuthStore();
        const userStore = useUserStore();

        // Get the current user username or display_name
        const username = userStore.user?.display_name || userStore.user?.username;

        // Send the request to the server to logout the user
        await this.axios.post("/api/auth/logout", {}, { disableErrorToast: true }).catch(() => console.log("Failed to logout backend"));

        // Remove the auth token and refresh token
        authStore.removeAccessToken();
        authStore.removeRefreshToken();

        try {
            // Redirect the user to the login page
            await this.router.push("/login");
        } catch (e) {
            // If the router push fails, redirect the user to the login page
            window.location.href = "/login";
        }

        // Show a goodbye message to the username else username
        this.infoToast(`Goodbye ${username || "User"}`);
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
            throw new Error("Your browser does not support WebAuthn");
        }

        // Make sure the browser supports webauthn autofill
        if (autofill && !(await this.browserSupportsWebAuthnAutofill())) {
            throw new Error("Your browser does not support WebAuthn Autofill");
        }

        // Check if the username is set
        if (!autofill && !this.username) {
            throw new Error("Username not provided");
        }

        // Fetch the authentication options from the server
        const authResp = await this.axios.get("/api/mfa/authentication", {
            params: {
                username: this.username,
            },
        });

        // Check if the response is successful
        if (authResp.status != 200) {
            throw new Error(authResp.data.message || "Failed to authenticate, please try again");
        }

        // Get the authentication options
        const authenticationOptions = authResp.data;

        // Start the authentication
        const assertion = await startAuthentication(authenticationOptions, autofill).catch(() => {
            // PATCH: Fix error when user cancels MFA authentication
            console.log("Authentication has been cancelled");
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
            throw new Error(e.data.message || "Failed to authenticate, please try again");
        });

        // Check if the response is null
        if (!authResp2) return;

        // Handle the authenticated data
        return this.handleAuthData(authResp2.data.auth.user, authResp2.data.auth.token, authResp2.data.auth.refresh_token);
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

export default Auth;
