# Subpath Support for Wizarr

This document describes the changes made to support running Wizarr under a custom path (e.g., `midominio.com/wizarr`) behind a reverse proxy.

## The Problem

When running Wizarr behind a reverse proxy like nginx with a location block like:

```nginx
location /wizarr {
    proxy_pass http://localhost:5698/;
}
```

The application would show 404 errors because:
1. All blueprints were registered with hardcoded `/` prefixes
2. Static files were served from `/static` without considering the subpath
3. URL generation with `url_for()` didn't account for the custom path

## The Solution

### 1. Configurable `APPLICATION_ROOT` (app/config.py)

Added a new environment variable `APPLICATION_ROOT` that allows you to specify the base path:

```bash
APPLICATION_ROOT=/wizarr
```

If not set, it defaults to `/` (root path).

### 2. Dynamic Blueprint Registration (app/__init__.py)

Modified the blueprint registration to prepend the `APPLICATION_ROOT` to each blueprint's `url_prefix`:

```python
# Example: if APPLICATION_ROOT=/wizarr
# /setup becomes /wizarr/setup
# /api becomes /wizarr/api
# etc.
```

### 3. Static Files Path (app/__init__.py)

Configured Flask to serve static files from the correct path:

```python
static_url_path=f"{app_root}/static"
```

### 4. Reverse Proxy Middleware (app/middleware.py)

Added a `ReverseProxyFix` middleware that:
- Reads `X-Forwarded-Prefix` header (sent by nginx/traefik)
- Sets `SCRIPT_NAME` for correct URL generation
- Handles `X-Forwarded-Proto` for HTTPS detection
- Handles `X-Forwarded-Host` for correct host detection

### 5. Onboarding Path Handling (app/middleware.py)

Updated the `require_onboarding()` function to handle paths correctly when running under a subpath.

## Usage

### Environment Variables

Set these in your Docker compose or environment:

```bash
# Required: the path where Wizarr is served
APPLICATION_ROOT=/wizarr

# Optional: if using HTTPS behind proxy
PREFERRED_URL_SCHEME=https
```

### Nginx Configuration

```nginx
location /wizarr {
    proxy_pass http://localhost:5698;
    proxy_set_header X-Forwarded-Prefix /wizarr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host:$server_port;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $host;
}
```

### Docker Compose Example

```yaml
services:
  wizarr:
    image: ghcr.io/wizarrrr/wizarr:latest
    container_name: wizarr
    environment:
      - APPLICATION_ROOT=/wizarr
      - PREFERRED_URL_SCHEME=https
    volumes:
      - ./config/wizarr:/config
```

### Traefik Configuration

If using Traefik, you can use `X-Forwarded-Prefix` middleware:

```yaml
labels:
  - "traefik.http.middlewares.wizarr-strip.stripprefix.prefixes=/wizarr"
  - "traefik.http.routers.wizarr.middlewares=wizarr-strip"
```

## Notes

- The `APPLICATION_ROOT` is used as a fallback if `X-Forwarded-Prefix` header is not present
- Static files are automatically served from the correct path
- All internal redirects and `url_for()` calls now generate correct URLs
- No changes are needed to templates or JavaScript files

## Testing

To test the subpath setup:

1. Set `APPLICATION_ROOT=/wizarr` environment variable
2. Start the application
3. Access via `http://localhost:5698/wizarr/` directly, or
4. Configure your reverse proxy and access via `https://midominio.com/wizarr`

## Files Modified

- `app/config.py` - Added `APPLICATION_ROOT` configuration
- `app/__init__.py` - Dynamic blueprint registration and static path configuration
- `app/middleware.py` - Added `ReverseProxyFix` middleware and updated path handling
