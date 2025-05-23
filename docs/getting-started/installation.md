# Installation

### Docker&#x20;

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
      - /path/to/appdata/config/database:/data/database
      - /path/to/appdata/config/wizard:/data/wizard_steps
    environment:
      - APP_URL=https://wizarr.domain.com #URL at which you will access and share 
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
  -v /path/to/appdata/config/database:/data/database \
  -v /path/to/appdata/config/wizard:/data/wizard_steps
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
