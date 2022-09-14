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
      - "APP_URL=https://join.domain.com"
  watchtower: #Optional but recommended, as Wizarr is still in development and will be updated frequently
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: wizarr --interval 30
```

2.  **Important** Edit Variables

    APP_URL: Public Facing Url of your Wizarr instance

3.  Run `docker compose up -d` or for older version: `docker-compose up -d`
4.  Access WebUI at http://localhost:5690 and setup your Plex Server

## Screenshots

*These may be out of date*

#### Light Mode
![alt](./screenshots/share.png)
![alt](./screenshots/invitation.png)
![alt](./screenshots/Download.png)
![alt](./screenshots/request.png)

#### Dark Mode
![alt](./screenshots/download_dark.png)
![alt](./screenshots/join_dark.png)
![alt](./screenshots/welcome_dark.png)
