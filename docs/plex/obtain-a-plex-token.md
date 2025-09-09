# Obtain a Plex token

## How to Get Your Plex Token

Some Wizarr features require your Plex authentication token. Here’s the simplest way to find it.

### 1. Open Plex in Your Browser

* Go to [https://app.plex.tv](https://app.plex.tv/) and log in.
* Open your **Plex Web App**.

### 2. Right-Click Any Item

* Right-click on a movie, show, or library item.
* Click **View Info**
* Select **View XML**

### 3. Copy the Token

* The XML page will open in a new tab.
* Look at the **URL in the address bar**.
* At the very end you’ll see `X-Plex-Token=...`

Example:

```
https://<server>:32400/library/metadata/12345?X-Plex-Token=abcd1234efgh5678
```

The part after `X-Plex-Token=` is your **Plex token**.

### 4. Keep It Safe

* Do **not** share this token publicly — it grants access to your Plex server.
* If it’s ever compromised, you can revoke it by signing out of all devices in your [Plex account settings](https://plex.tv/account).

