# Installation

## Installation

#### Docker

{% hint style="warning" %}
Be sure to replace`/path/to/appdata/config` in the below examples with a valid host directory path. If this volume mount is not configured correctly, your Wizarr settings/data will not be persisted when the container is recreated (e.g., when updating the image or rebooting your machine).

The `TZ` environment variable value should also be set to the [TZ database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) of your time zone!
{% endhint %}

{% tabs %}
{% tab title="Docker Compose (recommended)" %}
**Installation:**

Define the `wizarr` service in your `docker-compose.yml` as follows:

```yaml
---
services:
  wizarr:
    container_name: wizarr
    image: ghcr.io/wizarrrr/wizarr
    ports:
      - 5690:5690
    volumes:
      - /path/to/appdata:/data
    environment:
      - PUID=1000 #Set UID
      - PGID=1000 #Set GID
      - DISABLE_BUILTIN_AUTH=false #Set to true ONLY if you are using another auth provider (Authelia, Authentik, etc)
      - TZ=Europe/London #Set your timezone here
```

Then, start all services defined in the Compose file:

`docker compose up -d` **or** `docker-compose up -d`

**Updating**

Pull the latest image:

`docker compose pull wizarr` or `docker-compose pull wizarr`

Then, restart all services defined in the Compose file:

`docker compose up -d` or `docker-compose up -d`
{% endtab %}

{% tab title="Docker CLI" %}
**Installation**

<pre class="language-bash"><code class="lang-bash"><strong>docker run -d \
</strong>  --name wizarr \
  -e DISABLE_BUILTIN_AUTH=false \
  -e PUID=1000 -e PGID=1000 \
  -e TZ=Europe/London \
  -p 5690:5690 \
  -v /path/to/appdata:/data \
  --restart unless-stopped \
  ghcr.io/wizarrrr/wizarr
</code></pre>

**Updating**

Stop and remove the existing container:

```bash
docker stop wizarr && docker rm wizarr
```

Pull the latest image:

```bash
docker pull ghcr.io/wizarrrr/wizarr
```

Finally, run the container with the same parameters originally used to create the container:

```bash
docker run -d ...
```
{% endtab %}
{% endtabs %}

### Unraid

1. Ensure you have the **Community Applications** plugin installed.
2. Inside the **Community Applications** app store, search for **Wizarr**.
3. Click the **Install Button**.
4. On the following **Add Container** screen, make changes to the **Host Port** and **Host Path 1**(Appdata) as needed, as well as the environment variables.
5. Click apply and access "Wizarr" at your `<ServerIP:HostPort>` in a web browser.

## TrueNas Fangtooth

1.  Discover Apps

    ![image](https://github.com/user-attachments/assets/a99db34b-34f8-423c-8a56-617c87bf4c6a)
2.  Custom App

    ![image](https://github.com/user-attachments/assets/43e9ee74-3430-4dd5-8a82-0907f9877262)
3.  Quick install if you know what your doing.

    ![image](https://github.com/user-attachments/assets/fae99bb7-ee49-49cf-a611-007074a9ab5e)

_All other steps below are every single thing that needs to be changed. Also only things that need to be setup._

4. Use only what is used in pictures following. Don't change anything unless you know what your doing. For storage locations make changes to match your setup.

_Repository:_ [ghcr.io/wizarrrr/wizarr](ghcr.io/wizarrrr/wizarr/)

![image](https://github.com/user-attachments/assets/e4a91eb3-58d8-4ab5-8f1c-fdb775b408a6)

![image](https://github.com/user-attachments/assets/d44dec66-d520-4e2d-a6d3-6ea623c457c5)

![image](https://github.com/user-attachments/assets/f8ebb365-7404-4417-af70-b0f81a1275ba)

![image](https://github.com/user-attachments/assets/5888758f-4c4b-4756-b168-78647d5e6bd5)

![image](https://github.com/user-attachments/assets/d4e05d81-8e49-418c-a86c-1804ed0f002d)

![image](https://github.com/user-attachments/assets/c6737814-b871-46cd-900f-3a51e42bd4b9)

![image](https://github.com/user-attachments/assets/27c6e67b-eabe-4d40-b237-400d237f634e)

5.  Click Install

    ![image](https://github.com/user-attachments/assets/41a7a6df-cb5d-4379-8272-f622ac837235)
