# Wizarr
**Attention! Wizarr is still under development, you may experience issues.**

Wizarr is a automatic user invitation system for Plex. Create a unique link and share it to a user and they will automatically be invited to your Plex Server! They will even be guided to download the Plex client and instructions on how to use Overseerr!


![alt](./screenshots/welcome.png)


## Major Features Include

- Automatic Invitation to your Plex Server
- Secured invitation environment (HTTP AUTH)
- Plug and Play SSO Support (Via Forward-auth)\*
- Guide user on how to download Plex client
- Guide user on how to request Movies

*Don't forget to only include /invite in forward-auth

## Planned features

- Discord Bot Integration 
- Plex Quality guide 


## Installation

### Docker Compose (recommended)

1. Download Docker-compose file

```
version: "3.8"
services:
  wizarr:
    container_name: wizarr
    image: ghcr.io/wizarrrr/wizarr
    #image: ghcr.io/wizarrrr/wizarr:arm64 #For Arm64
    ports:
    - 5690:5690
    volumes:
      - ./data:/data/database
    environment:
      - "ADMIN_USERNAME=admin"
      - "ADMIN_PASSWORD=password"
      - "OVERSEERR_URL=https://overseerr.domain.com"
      - "PLEX_NAME=Wizarr"
      - "PLEX_URL=https://plex.domain.com"
      - "PLEX_TOKEN=XXXXXXXXXXXXXXXXXXX"
      - "PLEX_SECTIONS=Movies,TV Shows,Audiobooks"
      - "APP_URL=https://join.domain.com"
```

2.  **Important** Edit Variables

    ADMIN_USERNAME: A username for the invitation panel

    ADMIN_PASSWORD: A password for said invitation panel

    OVERSEERR_URL: Your overseerr instance

    PLEX_NAME: The name for your plex server!

    PLEX_URL: The URL of your plex server

    PLEX_TOKEN: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
    
    PLEX_SECTIONS: Comma Seperated list of Plex Libraries you wish to share (No unecessary spaces!)

    APP_URL: Public Facing Url of your Wizarr instance

3.  Run `docker compose up -d` or for older version: `docker-compose up -d`
4.  Access WebUI at http://localhost:5690

## Screenshots

*These may be out of date*

![alt](./screenshots/share.png)
![alt](./screenshots/invitation.png)
![alt](./screenshots/Download.png)
![alt](./screenshots/request.png)