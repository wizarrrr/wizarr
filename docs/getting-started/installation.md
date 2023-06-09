# Installation

### Docker

{% hint style="warning" %}
Be sure to replace`/path/to/appdata/config` in the below examples with a valid host directory path. If this volume mount is not configured correctly, your Wizarr settings/data will not be persisted when the container is recreated (e.g., when updating the image or rebooting your machine).

The `TZ` environment variable value should also be set to the [TZ database name](https://en.wikipedia.org/wiki/List\_of\_tz\_database\_time\_zones) of your time zone!
{% endhint %}

{% tabs %}
{% tab title="Docker Compose (recommended)" %}
**Installation:**

Define the `wizarr` service in your `docker-compose.yml` as follows:

```yaml
---
version: "3.8"
services:
  wizarr:
    container_name: wizarr
    image: ghcr.io/wizarrrr/wizarr
    #user: 1000:1000 #Optional but recommended, sets the user uid that Wizarr will run with
    ports:
      - 5690:5690
    volumes:
      - /path/to/appdata/config:/data/database
    environment:
      - APP_URL=https://wizarr.domain.com #URL at which you will access and share 
      - MIN_PASSWORD_LENGTH=8 # Minimum password length required for new users (default: 8)
      - MAX_PASSWORD_LENGTH=20 # Maximum password length for new users (default: 20)
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

<pre class="language-docker"><code class="lang-docker"><strong>docker run -d \
</strong>  --name wizarr \
  -e APP_URL=https://wizarr.domain.com \
  -e DISABLE_BUILTIN_AUTH=false \
  -e TZ=Europe/London \
  -p 5690:5690 \
  -v /path/to/appdata/config:/data/database \
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

## Unraid

1. Ensure you have the **Community Applications** plugin installed.
2. Inside the **Community Applications** app store, search for **Wizarr**.
3. Click the **Install Button**.
4. On the following **Add Container** screen, make changes to the **Host Port** and **Host Path 1**(Appdata) as needed, as well as the environment variables.
5. Click apply and access "Wizarr" at your `<ServerIP:HostPort>` in a web browser.
