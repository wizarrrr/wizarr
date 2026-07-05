from flask import current_app, redirect, request, url_for

from app.models import Settings


def require_onboarding():
    # Get the current path
    # Note: PATH_INFO has the prefix stripped by ReverseProxyFix middleware
    # but request.path includes SCRIPT_NAME, so we need to get the actual path
    path = request.path

    # Get SCRIPT_NAME (set by middleware if APPLICATION_ROOT is configured)
    script_name = request.script_root or ""

    # Remove SCRIPT_NAME prefix to get the actual route path
    if script_name and path.startswith(script_name):
        path = path[len(script_name) :] or "/"

    if path.startswith(("/setup", "/static", "/settings", "/api")):
        return None

    # Skip onboarding check during testing
    if current_app.config.get("TESTING"):
        return None

    # Check if an admin user exists
    admin_setting = Settings.query.filter_by(key="admin_username").first()
    if not admin_setting or not admin_setting.value:
        return redirect(url_for("setup.onboarding"))
    return None
    # Allow access to the application even if no MediaServer has been configured yet.
    # Users can add servers later via the Settings page.


class ReverseProxyFix:
    """Middleware to handle reverse proxy headers for subpath support.

    Handles both smart proxies (with X-Forwarded-Prefix header) and
    dumb proxies (that strip the prefix but don't send the header).
    """

    def __init__(self, wsgi_app, flask_app):
        self.wsgi_app = wsgi_app
        self.flask_app = flask_app  # Reference to Flask app for config access

    def __call__(self, environ, start_response):
        app_root = self.flask_app.config.get("APPLICATION_ROOT", "/")
        path_info = environ.get("PATH_INFO", "/")

        # Special case: /health endpoint should always work for Docker healthcheck
        # even without the prefix (internal health checks bypass the proxy)
        is_health_check = path_info in {"/health", "/health/"}
        # Check if request is from localhost (internal/Docker healthcheck)
        remote_addr = environ.get("REMOTE_ADDR", "")
        # Handle multiple IPs in X-Forwarded-For
        x_forwarded_for = environ.get("HTTP_X_FORWARDED_FOR", "")
        client_ip = (
            x_forwarded_for.split(",")[0].strip() if x_forwarded_for else remote_addr
        )
        local_addresses = {"127.0.0.1", "::1", "localhost"}
        is_local = client_ip in local_addresses or remote_addr in local_addresses

        # Determine the effective prefix
        forwarded_prefix = environ.get("HTTP_X_FORWARDED_PREFIX", "").rstrip("/")
        configured_prefix = app_root.rstrip("/")
        effective_prefix = forwarded_prefix or configured_prefix

        # Skip prefix handling only for local health checks
        if not (is_health_check and is_local) and effective_prefix:
            # Always set SCRIPT_NAME so url_for() generates correct URLs with prefix
            environ["SCRIPT_NAME"] = effective_prefix

            # Proxies may preserve or strip the prefix. Normalize either form.
            if path_info.startswith(effective_prefix):
                environ["PATH_INFO"] = path_info[len(effective_prefix) :] or "/"

        # Handle X-Forwarded-Proto for HTTPS detection
        forwarded_proto = environ.get("HTTP_X_FORWARDED_PROTO", "")
        if forwarded_proto:
            environ["wsgi.url_scheme"] = forwarded_proto

        # Handle X-Forwarded-Host
        forwarded_host = environ.get("HTTP_X_FORWARDED_HOST", "")
        if forwarded_host:
            environ["HTTP_HOST"] = forwarded_host

        return self.wsgi_app(environ, start_response)
