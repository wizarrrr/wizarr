import logging

import requests
from flask_babel import _
from plexapi.exceptions import PlexApiException
from plexapi.server import PlexServer
from requests import exceptions as req_exc


# Raised when a server returns a non-200 status code.
class ServerResponseError(Exception):
    def __init__(self, status_code: int, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(
            _("Server returned status code %(status_code)s", status_code=status_code)
        )


# Handle connection errors for both Plex and Jellyfin servers.
def handle_connection_error(e: Exception, server_type: str) -> tuple[bool, str]:
    if isinstance(e, ServerResponseError):
        error_msg = str(e)
        logging.error("%s check failed: %s → %s", server_type, e.url, e.status_code)
    elif isinstance(e, PlexApiException):
        error_msg = _(
            "%(server_type)s server returned an error: %(error)s",
            server_type=server_type,
            error=str(e),
        )
        logging.error("%s API error: %s", server_type, str(e))
    elif isinstance(e, req_exc.ConnectionError):
        error_msg = _(
            "Could not connect to the %(server_type)s server. Please check if the server is running and the URL is correct.",
            server_type=server_type,
        )
        logging.error("%s connection error: %s", server_type, str(e))
    elif isinstance(e, req_exc.Timeout):
        error_msg = _(
            "Connection to %(server_type)s server timed out. Please check if the server is running and accessible.",
            server_type=server_type,
        )
        logging.error("%s connection timeout", server_type)
    elif isinstance(e, req_exc.RequestException):
        error_msg = _(
            "An error occurred while connecting to the %(server_type)s server: %(error)s",
            server_type=server_type,
            error=str(e),
        )
        logging.error("%s request error: %s", server_type, str(e))
    else:
        error_msg = _(
            "An unexpected error occurred while connecting to the %(server_type)s server: %(error)s",
            server_type=server_type,
            error=str(e),
        )
        logging.error("%s check failed: %s", server_type, str(e), exc_info=True)
    return False, error_msg


def check_plex(url: str, token: str) -> tuple[bool, str]:
    try:
        PlexServer(url, token=token)
        return True, ""
    except Exception as e:
        return handle_connection_error(e, _("Plex"))


def check_jellyfin_or_emby_internal(url: str, token: str) -> tuple[bool, str]:
    resp = requests.get(f"{url}/Users", headers={"X-Emby-Token": token}, timeout=10)
    if resp.status_code != 200:
        raise ServerResponseError(resp.status_code, resp.url)
    return True, ""


def check_jellyfin(url: str, token: str) -> tuple[bool, str]:
    try:
        return check_jellyfin_or_emby_internal(url, token)
    except Exception as e:
        return handle_connection_error(e, _("Jellyfin"))


def check_emby(url: str, token: str) -> tuple[bool, str]:
    try:
        return check_jellyfin_or_emby_internal(url, token)
    except Exception as e:
        return handle_connection_error(e, _("Emby"))


def check_audiobookshelf(url: str, token: str) -> tuple[bool, str]:
    """Validate Audiobookshelf credentials.

    The most lightweight endpoint to probe is ``/ping`` which returns
    ``{"success": true}`` without requiring authentication.  When a
    token is provided we additionally fetch ``/api/libraries`` to verify
    the token works and that we can access the libraries list.
    """
    try:
        # 1) base connectivity – even works on brand-new instances
        resp = requests.get(f"{url.rstrip('/')}/ping", timeout=10)
        if resp.status_code != 200:
            raise ServerResponseError(resp.status_code, resp.url)

        if token:
            headers = {"Authorization": f"Bearer {token}"}
            lib_resp = requests.get(
                f"{url.rstrip('/')}/api/libraries", headers=headers, timeout=10
            )
            if lib_resp.status_code != 200:
                raise ServerResponseError(lib_resp.status_code, lib_resp.url)
        return True, ""
    except Exception as e:
        return handle_connection_error(e, _("Audiobookshelf"))


# ---------------------------------------------------------------------------
# RomM – new media-server backend
# ---------------------------------------------------------------------------


def check_romm(url: str, token: str) -> tuple[bool, str]:
    """Quick connectivity check for a RomM instance.

    We perform a lightweight GET request to ``/api/platforms`` which is
    available to any authenticated user and returns a list of platforms in
    JSON.  When *token* is set we send it as a *Basic* header.
    """
    try:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Basic {token}"

        resp = requests.get(
            f"{url.rstrip('/')}/api/platforms", headers=headers, timeout=10
        )
        if resp.status_code != 200:
            raise ServerResponseError(resp.status_code, resp.url)
        # Basic sanity check – ensure response is JSON list
        if not isinstance(resp.json(), list):
            raise ValueError("Unexpected RomM response format")
        return True, ""
    except Exception as e:
        return handle_connection_error(e, _("RomM"))


def check_komga(url: str, token: str) -> tuple[bool, str]:
    """Quick connectivity check for a Komga instance.

    We perform a lightweight GET request to ``/api/v1/libraries`` which is
    available to authenticated users and returns a list of libraries in
    JSON. When *token* is set we send it as a *Bearer* header.
    """
    try:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        resp = requests.get(
            f"{url.rstrip('/')}/api/v1/libraries", headers=headers, timeout=10
        )
        if resp.status_code != 200:
            raise ServerResponseError(resp.status_code, resp.url)
        # Basic sanity check – ensure response is JSON list
        if not isinstance(resp.json(), list):
            raise ValueError("Unexpected Komga response format")
        return True, ""
    except Exception as e:
        return handle_connection_error(e, _("Komga"))


def check_kavita(url: str, token: str) -> tuple[bool, str]:
    """Quick connectivity check for a Kavita instance.

    We perform a lightweight GET request to ``/api/Health`` which is
    available to check server health. If an API key is provided, we authenticate
    to get a JWT token and test access to libraries.
    """
    try:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        # First check health endpoint (no auth required)
        resp = requests.get(
            f"{url.rstrip('/')}/api/Health", headers=headers, timeout=10
        )
        if resp.status_code != 200:
            raise ServerResponseError(resp.status_code, resp.url)

        # If API key provided, authenticate and test access
        if token:
            # Step 1: Use API key to get JWT token
            auth_url = f"{url.rstrip('/')}/api/Plugin/authenticate"
            auth_params = {"apiKey": token, "pluginName": "Wizarr"}
            auth_resp = requests.post(
                auth_url, params=auth_params, headers=headers, timeout=10
            )
            if auth_resp.status_code != 200:
                raise ServerResponseError(auth_resp.status_code, auth_resp.url)

            auth_data = auth_resp.json()
            jwt_token = auth_data.get("token", "")
            if not jwt_token:
                raise ValueError("No JWT token returned from Kavita authentication")

            # Step 2: Use JWT token to test library access
            jwt_headers = {**headers, "Authorization": f"Bearer {jwt_token}"}
            lib_resp = requests.get(
                f"{url.rstrip('/')}/api/Library/libraries",
                headers=jwt_headers,
                timeout=10,
            )
            if lib_resp.status_code != 200:
                raise ServerResponseError(lib_resp.status_code, lib_resp.url)

            # Basic sanity check – ensure response is JSON list
            if not isinstance(lib_resp.json(), list):
                raise ValueError("Unexpected Kavita response format")

        return True, ""
    except Exception as e:
        return handle_connection_error(e, _("Kavita"))


def check_navidrome(url: str, token: str) -> tuple[bool, str]:
    """Quick connectivity check for a Navidrome instance.

    We perform a lightweight request to the ``/rest/ping`` endpoint which is
    available to check server connectivity using the Subsonic API.
    When *token* (password) is provided, we authenticate using the salted hash method.
    """
    try:
        import hashlib
        import random
        import string

        # Build Subsonic API authentication parameters
        params = {
            "u": "admin",  # Default username for API access
            "v": "1.16.1",  # Supported API version
            "c": "wizarr",  # Client identifier
            "f": "json",  # Response format
        }

        if token:
            # Generate random salt for secure authentication
            salt = "".join(random.choices(string.ascii_letters + string.digits, k=6))

            # Create SHA-256 hash of password + salt (prefer strong hash if supported by Navidrome/Subsonic API)
            token_hash = hashlib.sha256((token + salt).encode()).hexdigest()
            # If the server requires MD5, revert to MD5 and document the reason:
            # token_hash = hashlib.md5((token + salt).encode()).hexdigest()  # Protocol-mandated, insecure

            params.update(
                {
                    "t": token_hash,
                    "s": salt,
                }
            )
        else:
            # If no token provided, try without authentication (some endpoints allow this)
            params["p"] = ""

        resp = requests.get(f"{url.rstrip('/')}/rest/ping", params=params, timeout=10)
        if resp.status_code != 200:
            raise ServerResponseError(resp.status_code, resp.url)

        # Check for Subsonic API errors in response
        data = resp.json()
        subsonic_response = data.get("subsonic-response", {})
        if subsonic_response.get("status") != "ok":
            error = subsonic_response.get("error", {})
            raise ValueError(
                f"Navidrome API error: {error.get('message', 'Unknown error')}"
            )

        return True, ""
    except Exception as e:
        return handle_connection_error(e, _("Navidrome"))
