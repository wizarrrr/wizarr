<h1 align="center">Wizarr</h1>
<h3 align="center">The Free Media Invitation System</h3>

---


<p align="center">
<img src="https://raw.githubusercontent.com/Wizarrrr/wizarr/master/apps/wizarr-frontend/src/assets/img/wizard.png" height="200">
<br/>
<br/>
<a href="https://github.com/wizarrrr/wizarr/blob/master/LICENSE.md"><img alt="GPL 2.0 License" src="https://img.shields.io/github/license/wizarrrr/wizarr.svg"/></a>
<a href="https://github.com/wizarrrr/wizarr/releases"><img alt="Current Release" src="https://img.shields.io/github/release/wizarrrr/wizarr.svg"/></a>
<a href="https://features.wizarr.dev" style="text-decoration: none"><img alt="Submit Feature Requests" src="https://img.shields.io/badge/vote_now-features?label=features"/></a>
<a href="https://discord.gg/XXCz7aM3ak"><img alt="Chat on Discord" src="https://img.shields.io/discord/1020742926856372224"/></a>
<a href="https://www.reddit.com/r/wizarr"><img alt="Join our Subreddit" src="https://img.shields.io/badge/reddit-r%2Fwizarr-%23FF5700.svg"/></a>
<a href="https://github.com/Wizarrrr/wizarr/issues"><img alt="Github Issue" src="https://img.shields.io/github/issues/wizarrrr/wizarr"/></a>
<a href="https://github.com/Wizarrrr/wizarr/actions/workflows/beta-ci.yml"><img alt="Github Build" src="https://img.shields.io/github/actions/workflow/status/wizarrrr/wizarr/beta-ci.yml"/></a>
</p>

---

# WIZARR NOTICE

Wizzar is back in development! You can test the new beta using `ghcr.io/wizarrrr/wizarr:beta` as your image selection. We are working very hard to make Wizarr even better than before! :blush:

If you wish to stay up-to-date with our progress, make sure to join our [Discord](https://discord.gg/XXCz7aM3ak) server and check the `#beta-updates` channel.

---

## What is Wizarr?

Wizarr is an automated user invitation system for Plex/Jellyfin/Emby. You can create a unique link, share it with a user, and they will be invited to your Media Server after they complete the simple signup process!

## Major Features Include

-   Automatic Invitation System to your Media Server (Plex/Jellyfin/Emby)
-   Support for Passkey authentication for Admin Users
-   Create multiple invitations with different configurations
-   Make invitations and users expire after a certain amount of time
-   Automatically add users to your Requesting System (Jellyseerr/Overseerr)
-   Invite users to your Discord server through the onboarding process
-   Multi-Language Support
-   Multiple Admin Users with different permissions
-   API for Developers with Swagger UI
-   Light and Dark Mode Support
-   Session Management for Admin Users
-   Scheduled Tasks to keep Wizarr updated with your Media Server
-   Live logs directly from the Wizarr Web UI

## What is the difference between V3 and V4?

V3 is the current stable version of Wizarr; It is a fully functional system that allows you to invite users to your Plex/Jellyfin/Emby media server. V4 is the next iteration which will expand on features considerably. For now, however, a few changes have already been added:

- Administrator password change
- Linking and unlinking your Discord server to/from the onboarding process
- Updated logo and branding
  
## Major features to come in V4 will include

-   Custom onboarding builder
-   Added API Endpoints (already partially available)
-   Plex/Jellyfin/Emby granular user permissions
-   Discord invite request integration
-   Multi-Server Support
-   SMTP Support for notifications and user invites
-   OAuth Support with custom providers
-   2FA Support for Admin Users
-   Built in Update System
-   Plugin Store
-   and much more!

## Getting Started

You can install the stable version of Wizarr by following the instructions below.

```
docker run -d \
    --name wizarr \
    -p 5690:5690 \
    -v ./wizarr/database:/data/database \
    ghcr.io/wizarrrr/wizarr:latest
```

```
---
version: "3.5"
services:
  wizarr:
    container_name: wizarr
    image: ghcr.io/wizarrrr/wizarr:latest
    ports:
      - 5690:5690
    volumes:
      - ./wizarr/database:/data/database
```

## Documentation

Check out our documentation for instructions on how to install and run Wizarr!
[View Documentation](https://github.com/Wizarrrr/wizarr/blob/master/docs/setup/README.md).

If you encounter any issues please don't hesitate to visit our [Discord](https://discord.gg/XXCz7aM3ak) server and ask for help, we would be happy to help.

<a href="https://discord.gg/XXCz7aM3ak">
<img alt="Chat on Discord" src="https://img.shields.io/discord/1020742926856372224"/>
</a>

## Contributing

If you wish to contribute to our project you can check out our contributing guide [here](https://github.com/wizarrrr/wizarr/blob/develop/CONTRIBUTING.md).

## Thank you

A big thank you ❤️ to these amazing people for contributing to this project!

<a href="https://github.com/wizarrrr/wizarr/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=wizarrrr/wizarr" />
</a>
