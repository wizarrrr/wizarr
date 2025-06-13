import logging, requests
from plexapi.server import PlexServer
from requests.exceptions import RequestException
from plexapi.exceptions import PlexApiException
from typing import Callable, Any, Tuple
from flask_babel import _

# Raised when a server returns a non-200 status code.
class ServerResponseError(Exception):
    def __init__(self, status_code: int, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(_("Server returned status code %(status_code)s", status_code=status_code))

# Handle connection errors for both Plex and Jellyfin servers.
def handle_connection_error(e: Exception, server_type: str) -> Tuple[bool, str]:
    if isinstance(e, ServerResponseError):
        error_msg = str(e)
        logging.error("%s check failed: %s → %s", server_type, e.url, e.status_code)
    elif isinstance(e, PlexApiException):
        error_msg = _("%(server_type)s server returned an error: %(error)s", server_type=server_type, error=str(e))
        logging.error("%s API error: %s", server_type, str(e))
    elif isinstance(e, requests.exceptions.ConnectionError):
        error_msg = _("Could not connect to the %(server_type)s server. Please check if the server is running and the URL is correct.", server_type=server_type)
        logging.error("%s connection error: %s", server_type, str(e))
    elif isinstance(e, requests.exceptions.Timeout):
        error_msg = _("Connection to %(server_type)s server timed out. Please check if the server is running and accessible.", server_type=server_type)
        logging.error("%s connection timeout", server_type)
    elif isinstance(e, requests.exceptions.RequestException):
        error_msg = _("An error occurred while connecting to the %(server_type)s server: %(error)s", server_type=server_type, error=str(e))
        logging.error("%s request error: %s", server_type, str(e))
    else:
        error_msg = _("An unexpected error occurred while connecting to the %(server_type)s server: %(error)s", server_type=server_type, error=str(e))
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
            lib_resp = requests.get(f"{url.rstrip('/')}/api/libraries", headers=headers, timeout=10)
            if lib_resp.status_code != 200:
                raise ServerResponseError(lib_resp.status_code, lib_resp.url)
        return True, ""
    except Exception as e:
        return handle_connection_error(e, _("Audiobookshelf"))
