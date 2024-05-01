# Reverse Proxy

## Nginx

{% tabs %}
{% tab title="SWAG" %}
Create a new file `wizarr.subdomain.conf` in `proxy-confs` with the following configuration:

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;

    server_name wizarr.*;

    include /config/nginx/ssl.conf;

    client_max_body_size 0;

    location / {
        include /config/nginx/proxy.conf;
        resolver 127.0.0.11 valid=30s;
        set $upstream_app wizarr;
        set $upstream_port 5690;
        set $upstream_proto http;
        proxy_pass $upstream_proto://$upstream_app:$upstream_port;
    }
}
```
{% endtab %}

{% tab title="Nginx Proxy Manager" %}
Add a new proxy host with the following settings:

**Details**

* **Domain Names:** Your desired external wizarr hostname; e.g., `wizarr.example.com`
* **Scheme:** `http`
* **Forward Hostname / IP:** Internal wizarr hostname or IP
* **Forward Port:** `5690`
* **Cache Assets:** yes
* **Block Common Exploits:** yes
* **Websocket Support:** yes

**SSL**

* **SSL Certificate:** Select one of the options; if you are not sure, pick “Request a new SSL Certificate”
* **Force SSL:** yes
* **HTTP/2 Support:** yes
{% endtab %}

{% tab title="Subdomain" %}
Add the following configuration to a new file `/etc/nginx/sites-available/wizarr.example.com.conf`:

```nginx
server {
    listen 80;
    server_name wizarr.example.com;
    # Do not modify the line below as it is built from the directive above
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    http2 on;
    server_name wizarr.example.com;

    ssl_certificate /etc/letsencrypt/live/wizarr.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wizarr.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5690;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }
}
```

Then, create a symlink to `/etc/nginx/sites-enabled`:

```bash
sudo ln -s /etc/nginx/sites-available/wizarr.example.com.conf /etc/nginx/sites-enabled/wizarr.example.com.conf
```
{% endtab %}
{% endtabs %}

## Traefik (v2)

Add the following labels to the wizarr service in your `docker-compose.yml` file:

```
labels:
  - "traefik.enable=true"
  ## HTTP Routers
  - "traefik.http.routers.wizarr-rtr.entrypoints=https"
  - "traefik.http.routers.wizarr-rtr.rule=Host(`wizarr.domain.com`)"
  - "traefik.http.routers.wizarr-rtr.tls=true"
  ## HTTP Services
  - "traefik.http.routers.wizarr-rtr.service=wizarr-svc"
  - "traefik.http.services.wizarr-svc.loadbalancer.server.port=5690"
```

For more information, please refer to the [Traefik documentation](https://doc.traefik.io/traefik/user-guides/docker-compose/basic-example/).

## Caddy

{% tabs %}
{% tab title="Subdomain" %}
Add the following site block to your Caddyfile:

```
wizarr.example.com {
    reverse_proxy http://127.0.0.1:5690
}
```
{% endtab %}

{% tab title="Path" %}
You need the [response replacement](https://github.com/caddyserver/replace-response) module to use this config.

Add the following site block to your Caddyfile:

```
plex.example.com {
    redir /wizarr /wizarr/admin

    handle_path /wizarr/* {
        replace {
            "href=\"/"      "href=\"/wizarr/"
            "action=\"/"    "action=\"/wizarr/"
            "\"/static"       "\"/wizarr/static"
            "hx-post=\"/"   "hx-post=\"/wizarr/"
            "hx-get=\"/"    "hx-get=\"/wizarr/"
            "scan=\"/"      "href=\"/wizarr/"
            "/scan"         "/wizarr/scan"
            # include in join code path copy
            "navigator.clipboard.writeText(url + \"/i/\" + invite_code);" "navigator.clipboard.writeText(url + \"/wizarr/i/\" + invite_code);"
        }

        # Your wizarr backend
        reverse_proxy http://127.0.0.1:5690
    }
    # Your main service that you want at /
    reverse_proxy http://127.0.0.1:5055
}
```
{% endtab %}
{% endtabs %}
