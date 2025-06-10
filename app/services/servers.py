import logging, requests
from plexapi.server import PlexServer
from requests.exceptions import RequestException
from plexapi.exceptions import PlexApiException
from typing import Callable, Any, Tuple

# Raised when a server returns a non-200 status code.
class ServerResponseError(Exception):
    def __init__(self, status_code: int, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(f"Server returned status code {status_code}")

# Handle connection errors for both Plex and Jellyfin servers.
def handle_connection_error(e: Exception, server_type: str) -> Tuple[bool, str]:
    if isinstance(e, ServerResponseError):
        error_msg = str(e)
        logging.error("%s check failed: %s → %s", server_type, e.url, e.status_code)
    elif isinstance(e, PlexApiException):
        error_msg = f"{server_type} server returned an error: {str(e)}"
        logging.error("%s API error: %s", server_type, str(e))
    elif isinstance(e, requests.exceptions.ConnectionError):
        error_msg = f"Could not connect to the {server_type} server. Please check if the server is running and the URL is correct."
        logging.error("%s connection error: %s", server_type, str(e))
    elif isinstance(e, requests.exceptions.Timeout):
        error_msg = f"Connection to {server_type} server timed out. Please check if the server is running and accessible."
        logging.error("%s connection timeout", server_type)
    elif isinstance(e, requests.exceptions.RequestException):
        error_msg = f"An error occurred while connecting to the {server_type} server: {str(e)}"
        logging.error("%s request error: %s", server_type, str(e))
    else:
        error_msg = f"An unexpected error occurred while connecting to the {server_type} server: {str(e)}"
        logging.error("%s check failed: %s", server_type, str(e), exc_info=True)
    return False, error_msg

def check_plex(url: str, token: str) -> tuple[bool, str]:
    try:
        PlexServer(url, token=token)
        return True, ""
    except Exception as e:
        return handle_connection_error(e, "Plex")

def check_jellyfin(url: str, token: str) -> tuple[bool, str]:
    try:
        resp = requests.get(f"{url}/Users", headers={"X-Emby-Token": token}, timeout=10)
        if resp.status_code != 200:
            raise ServerResponseError(resp.status_code, resp.url)
        return True, ""
    except Exception as e:
        return handle_connection_error(e, "Jellyfin")
