# Wizarr

Wizarr is a automatic user invitation system for Plex. Create a unique link and share it to a user and they will automatically be invited to your Plex Server! They will even be guided to download the Plex client and instructions on how to use Overseerr!

![alt](./screenshots/invitation.png)

## Major Features Include

* Automatic Invitation to your Plex Server
* Secured invitation environment (HTTP AUTH)
* Plug and Play SSO Support (Via Forward-auth)*
* Guide user on how to download Plex client
* Guide user on how to request Movies

## Installation

### Docker Compose (recommended)

1. Download Docker-compose file
```
version: "3.8"
services:
  wizarr:
    container_name: wizarr
    image: wizarr/wizarr
    ports: 
    - 8080:8080
    volumes:
      - ./data:/data/database
    environment:
      - "ADMIN_USERNAME=admin"
      - "ADMIN_PASSWORD=password"
      - "OVERSEERR_URL=https://overseerr.domain.com"
      - "PLEX_NAME=Wizarr"
      - "PLEX_URL=https://plex.domain.com"
      - "PLEX_TOKEN=XXXXXXXXXXXXXXXXXXX"
      - "APP_URL=https://join.domain.com"
```
 2. **Important** Edit Variables
 3. Run `docker compose up -d` or for older version: `docker-compose up -d` 
 4. Access WebUI at http://localhost:8080