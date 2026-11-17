"""Service for resolving the base URL used in invite and password-reset links.

Wizarr can be reached at different addresses depending on how an admin is
connected (a LAN IP, a VPN address, a reverse-proxy hostname, `localhost`,
etc.). Without an explicit override, invite/reset links are built from
whatever address the *admin's browser* happened to be using at the moment
the link was generated (see `HX-Current-URL` / `request.url_root` below) --
which is frequently unreachable for the person actually receiving the
invite (see https://github.com/wizarrrr/wizarr/issues/244).

Setting a "Public Wizarr URL" in General settings overrides that guess with
a single, fixed, known-reachable address, independent of where the admin
is browsing from.
"""

from urllib.parse import urlparse

from flask import request

from app.models import Settings

SETTING_KEY = "public_url"


def get_configured_public_url() -> str | None:
    """Return the admin-configured public URL, normalized, or None if unset.

    Normalization strips surrounding whitespace and any trailing slash so
    callers can safely do ``f"{base}/j/{code}"`` without producing a
    double slash.
    """
    setting = Settings.query.filter_by(key=SETTING_KEY).first()
    if not setting or not setting.value:
        return None

    value = setting.value.strip().rstrip("/")
    return value or None


def resolve_base_url() -> str:
    """Resolve the base URL to use when building an invite/reset link.

    Priority:
    1. The configured "Public Wizarr URL" general setting, if set -- this
       is a deliberate admin choice and always wins.
    2. The HTMX ``HX-Current-URL`` header, which reflects the admin's
       actual browser address bar for HTMX partial requests (the
       historical behavior for the invite-creation modal).
    3. The current request's own root URL (the historical behavior for
       the password-reset modals).

    Must be called inside an active Flask request context.
    """
    configured = get_configured_public_url()
    if configured:
        return configured

    current_url = request.headers.get("HX-Current-URL")
    if current_url:
        parsed = urlparse(current_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"

    return request.url_root.rstrip("/")
