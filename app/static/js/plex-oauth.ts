import { PlexOauth, IPlexClientDetails } from "plex-oauth"

let clientInformation: IPlexClientDetails = {
    clientIdentifier: "<PROVIDE_UNIQUE_VALUE>", // This is a unique identifier used to identify your app with Plex.
    product: "Wizarr",              // Name of your application
    device: "Cloud",            // The type of device your application is running on
    version: "1",                               // Version of your application
    forwardUrl: "http://127.0.0.0:5000",       // Optional - Url to forward back to after signing in.
    platform: "Web",                            // Optional - Platform your application runs on - Defaults to 'Web'
    urlencode: true                             // Optional - If set to true, the output URL is url encoded, otherwise if not specified or 'false', the output URL will return as-is
}

let plexOauth = new PlexOauth(clientInformation);

// Get hosted UI URL and Pin Id
plexOauth.requestHostedLoginURL().then(data => {
    let [hostedUILink, pinId] = data;

    console.log(hostedUILink); // UI URL used to log into Plex

    /*
    * You can now navigate the user's browser to the 'hostedUILink'. This will include the forward URL
    * for your application, so when they have finished signing into Plex, they will be redirected back
    * to the specified URL. From there, you just need to perform a query to check for the auth token.
    * (See Below)
    */

   // Check for the auth token, once returning to the application
   plexOauth.checkForAuthToken(pinId).then(authToken => {
       console.log(authToken); // Returns the auth token if set, otherwise returns null

       // An auth token will only be null if the user never signs into the hosted UI, or you stop checking for a new one before they can log in
   }).catch(err => {
       throw err;
   });

}).catch(err => {
    throw err;
});