from schematics.types import URLType
from schematics.exceptions import ValidationError
from requests import get
from logging import error

def detect_server(server_url: str):
    """
    Detect what type of media server is running at the given url

    :param server_url: The url of the media server
    :type server_url: str

    :return: object
    """

    # Create URLType object
    url_validator = URLType(fqdn=False)

    # Create a url object
    url = url_validator.valid_url(server_url)

    # Check if the url is valid
    if not url:
        raise ValidationError("Invalid url, malformed input")

    # If the url has path, query, or fragment, raise an exception
    if url["query"] or url["frag"]:
        raise ValidationError("Invalid url, must be a base url")

    # Get host from url
    host = url["hostn"] or url["host4"] or url["host6"]

    # Construct the url from the server url
    server_url = f"{url['scheme']}://{host}"

    # Add the port if it exists
    if url["port"]:
        server_url += f":{url['port']}"

    # Add the path if it exists
    if url["path"] and url["path"] != "/":
        server_url += url["path"]

    # Map endpoints to server types
    endpoints = {
        "plex": "/identity",
        "jellyfin": "/System/Info/Public"
    }

    # Loop through the endpoints to find the server type
    for server_type, endpoint in endpoints.items():
        # Make the request, don't allow redirects, and set the timeout to 30 seconds
        try:
            response = get(f"{server_url}{endpoint}", allow_redirects=False, timeout=30)
        except Exception as e:
            error(e)
            continue

        # Check if the response is valid
        if response.status_code == 200:
            return {
                "server_type": server_type,
                "server_url": server_url
            }

    # Raise an exception if the server type is not found
    raise ConnectionError("Media Server could not be contacted")


def verify_server(server_url: str, server_api_key: str):
    """
    Verify that the api credentials are valid for the media server

    :param server_url: The url of the media server
    :type server_url: str

    :param server_api_key: The api key of the media server
    :type server_api_key: str

    :return: object
    """

    # Get the server type
    server = detect_server(server_url)
    server_type = server["server_type"]
    server_url = server["server_url"]

    # Map endpoints for verifying the server
    endpoints = {
        "plex": f"/connections?X-Plex-Token={server_api_key}",
        "jellyfin": f"/System/Info?api_key={server_api_key}"
    }

    # Build the url for the server
    server_url += endpoints[server_type]

    # Make the request, don't allow redirects, and set the timeout to 30 seconds
    try:
        response = get(server_url, allow_redirects=False, timeout=30)
    except ConnectionError as e:
        raise ConnectionError("Unable to connect to server") from e

    # Check if the response is valid
    if response.status_code == 200:
        return {
            "server_type": server_type,
            "server_url": server["server_url"]
        }

    # Raise an exception if the server type is not found
    raise ConnectionError("Unable to verify server")
