import type { IPlexClientDetails } from 'plex-oauth';
import { PlexOauth } from 'plex-oauth';
import bowser from 'bowser';
import { nanoid } from 'nanoid';

class PlexAuth {
    private plexOauth: PlexOauth;
    private browser = bowser.getParser(window.navigator.userAgent);

    // Default client details
    clientDetails: IPlexClientDetails = {
        clientIdentifier: nanoid(),
        product: 'Wizarr',
        device: this.browser.getOSName(),
        version: this.browser.getBrowserVersion(),
        platform: this.browser.getBrowserName(),
        urlencode: true,
    };

    // Construct PlexAuth with custom client details
    constructor(clientDetails: IPlexClientDetails | null = null) {
        this.plexOauth = new PlexOauth(clientDetails ?? this.clientDetails);
    }

    // Login to Plex
    async login(): Promise<string | null> {
        // Get the URL and pinId from Plex
        const [url, pinId] = await this.plexOauth.requestHostedLoginURL();

        // Create a popup window for the URL
        this.createPopUp(url);

        // Create a polling interval to check for the auth token
        const token = await this.plexOauth.checkForAuthToken(pinId, 1000, 120);

        // Return the auth token
        return token;
    }

    // Create a popup window for a URL
    private createPopUp(url: string) {
        setTimeout(() =>
            window.open(
                url,
                'Plex',
                'width=600, height=700, toolbar=no, menubar=no',
            ),
        );
    }
}

export default PlexAuth;
