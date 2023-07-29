import bowser from 'bowser';
import { nanoid } from 'nanoid';
import { IPlexClientDetails, PlexOauth } from 'plex-oauth';

import addToWindow from './addToWindow';

class PlexAuth {

    private plexOauth: PlexOauth;
    private browser = bowser.getParser(window.navigator.userAgent);
    private popup: Window | null = null;
    private timeout: number = 0;

    // Default client details
    clientDetails: IPlexClientDetails = {
        clientIdentifier: nanoid(),
        product: "Wizarr",
        device: this.browser.getOSName(),
        version: this.browser.getBrowserVersion(),
        platform: this.browser.getBrowserName(),
        urlencode: true
    }

    // Construct PlexAuth with custom client details
    constructor(clientDetails: IPlexClientDetails | null = null) {
        this.plexOauth = new PlexOauth(clientDetails ?? this.clientDetails);
        window.browser = this.browser;
    }

    // Login to Plex
    async login(): Promise<string | null> {
        // Get the URL and pinId from Plex
        const [url, pinId] = await this.requestHostedLoginURL();

        // If mobile, open the URL in a new tab
        if (this.browser.getPlatformType(true) == "mobile") {
            // Open the URL in a new tab
            this.createNewTab(url);
        } else {
            // Create a popup window using the URL
            this.createPopUp(url);
        }

        // Create a polling interval to check for the auth token
        const token = await this.createPollingInterval(pinId);

        // Close the popup window after 2 seconds when the token is received
        setTimeout(() => this.popup?.close(), 500);

        // Return the auth token
        return token;
    }

    // Request a hosted login URL from Plex
    private async requestHostedLoginURL(): Promise<[string, number]> {
        return await this.plexOauth.requestHostedLoginURL();
    }

    // Check for an auth token from Plex
    private async checkForAuthToken(pinId: number): Promise<string | null> {
        return await this.plexOauth.checkForAuthToken(pinId);
    }

    // Create a polling interval to check for the auth token
    private async createPollingInterval(pinId: number): Promise<string | null> {
        while (true) {
            if (this.popup?.closed) {
                return null;
            }

            this.timeout = this.timeout + 1;

            if (this.timeout > 45) {
                return null;
            }

            const token = await this.checkForAuthToken(pinId);

            if (token) {
                return token;
            }

            await new Promise(resolve => setTimeout(resolve, 800));
        }
    }

    // Create a popup window for a URL
    private createPopUp(url: string) {
        this.popup = window.open(url, "Plex", 'width=600, height=700, toolbar=no, menubar=no');
    }

    // Open URL in a new tab
    private createNewTab(url: string) {
        // F*ck you, Safari
        setTimeout(() => {
            this.popup = window.open(url, "_blank");
        });
    }
}

addToWindow(["PlexAuth"], PlexAuth);

export default PlexAuth;