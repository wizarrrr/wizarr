# Request Integration

## Introduction
Wizarr supports integration with [Jellyseerr](https://github.com/Fallenbagel/jellyseerr), [Overseerr](https://github.com/sct/overseerr) and [Ombi](https://github.com/Ombi-app/Ombi). This allows you to guide your users on how to request movies and tv shows after they have been invited to your media server. Wizarr will automatically add the user to the selected request software after they have inputted their sign in details.

## Setup
### Jellyseerr
1. Go to your Jellyseerr instance settings and copy the API key.
2. Go to your Wizarr instance settings and select Jellyseerr from the dropdown.
3. Input your Jellyseerr base URL.
4. Input your Jellyseerr API key.

### Overseerr
1. Go to your Overseerr instance settings and copy the API key.
2. Go to your Wizarr instance settings and select Overseerr from the dropdown.
3. Input your Overseerr base URL.
4. Input your Overseerr API key.

### Ombi
1. Go to your Ombi instance settings, then click "Configuration" and select "General" from the dropdown.
2. Copy the API key from the "API Key" field.
3. Go to your Wizarr instance settings and select Ombi from the dropdown.
4. Input your Ombi base URL.
5. Input your Ombi API key.

## Usage
Now when a user is invited to your media server, they will be automatically added to your request software. They will also be guided on how to request movies and tv shows. When a user expires or is deleted from Wizarr, they will also be removed from your request software.