"""Authlib-based OIDC client, built fresh from the stored ``OIDCConfiguration``.

Unlike a typical Authlib Flask app (where ``OAuth.register()`` is called once
at app-factory time with static config), Wizarr's OIDC provider is admin
configurable at runtime via the Settings UI. So instead we build a throwaway
``OAuth`` registry per request from whatever is currently in the database --
this mirrors the existing pattern of constructing a fresh ``LDAPClient(config)``
on every LDAP operation (see ``app/services/ldap/client.py``).

Registering a client with Authlib is just an in-memory dict write, so doing
it per-request has no real cost, and it means a config change in the
Settings UI takes effect on the very next login attempt with no restart.
"""

from __future__ import annotations

from authlib.integrations.flask_client import OAuth
from flask import current_app

from app.models import OIDCConfiguration

# The encryption helper lives under app.services.ldap because the Fernet key
# it uses (LDAP_OIDC_ENCRYPTION_KEY) was already named for both LDAP and OIDC
# secrets -- see app/services/ldap/encryption.py.
from app.services.ldap.encryption import decrypt_credential, encrypt_credential

_CLIENT_NAME = "wizarr_oidc"

__all__ = ["encrypt_credential", "get_oidc_client", "get_oidc_config"]


def get_oidc_config() -> OIDCConfiguration | None:
    """Return the (singleton) OIDC configuration row, if any."""
    return OIDCConfiguration.query.first()


def get_oidc_client(config: OIDCConfiguration | None = None):
    """Return an Authlib remote-app client for *config*, or ``None``.

    Returns ``None`` when OIDC isn't configured/enabled so callers can fail
    closed without special-casing exceptions.
    """
    if config is None:
        config = get_oidc_config()

    if not config or not config.enabled:
        return None

    client_secret = (
        decrypt_credential(config.client_secret_encrypted)
        if config.client_secret_encrypted
        else None
    )

    oauth = OAuth(current_app)
    # Re-registering under the same name on every call simply overwrites the
    # previous in-memory entry -- safe, and means edited settings apply
    # immediately.
    oauth.register(
        name=_CLIENT_NAME,
        client_id=config.client_id,
        client_secret=client_secret,
        server_metadata_url=config.discovery_url,
        client_kwargs={
            "scope": config.scopes or "openid profile email",
            "code_challenge_method": "S256",  # PKCE
        },
    )
    return oauth.create_client(_CLIENT_NAME)
