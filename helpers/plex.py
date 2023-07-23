from typing import Optional

from plexapi.myplex import PlexServer, LibrarySection, MyPlexUser
from pydantic import HttpUrl

from .settings import get_settings

# ANCHOR - Get Plex Server
def get_plex_server(server_api_key: Optional[str] = None, server_url: Optional[str or HttpUrl] = None) -> PlexServer:
    """Get a PlexServer object
    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str or HttpUrl] - If not provided, will get from database.

    :return: A PlexServer object
    """

    # Get required settings
    if not server_api_key or not server_url:
        settings = get_settings(["server_api_key", "server_url"])
        server_url = server_url or settings.get("server_url", None)
        server_api_key = server_api_key or settings.get("server_api_key", None)

    # Create PlexServer object
    plex_server = PlexServer(server_url, server_api_key)

    # Return PlexServer object
    return plex_server


# ANCHOR - Plex Scan Libraries
def scan_plex_libraries(server_api_key: Optional[str] = None, server_url: Optional[str or HttpUrl] = None) -> list[LibrarySection]:
    """Scan all Plex libraries
    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str or HttpUrl] - If not provided, will get from database.

    :return: list[dict] - A list of all libraries
    """

    # Get the PlexServer object
    plex = get_plex_server(server_api_key, server_url)

    # Get the raw libraries
    response: list[LibrarySection] = plex.library.sections()

    # Raise exception if raw_libraries is not a list
    if not isinstance(response, list):
        raise TypeError("Plex API returned invalid data.")

    # Return the libraries
    return response


# ANCHOR - Plex Get Users
def get_plex_users(server_api_key: Optional[str] = None, server_url: Optional[str or HttpUrl] = None) -> list[MyPlexUser]:
    """Get all Plex users
    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str or HttpUrl] - If not provided, will get from database.

    :return: list[dict] - A list of all users
    """

    # Get the PlexServer object
    plex = get_plex_server(server_api_key, server_url)

    # Get the raw users
    response: list[MyPlexUser] = plex.myPlexAccount().users()

    # Raise exception if raw_users is not a list
    if not isinstance(response, list):
        raise TypeError("Plex API returned invalid data.")

    # Return the users
    return response


# ANCHOR - Plex Get User
def get_plex_user(user_id: str, server_api_key: Optional[str] = None, server_url: Optional[str or HttpUrl] = None) -> MyPlexUser:
    """Get a Plex user
    :param user_id: The id of the user
    :type user_id: str - [usernames, email, id]

    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str or HttpUrl] - If not provided, will get from database.

    :return: dict - A user
    """

    # Get the PlexServer object
    plex = get_plex_server(server_api_key, server_url)

    # Get the raw user
    response: MyPlexUser = plex.myPlexAccount().user(user_id)

    # Raise exception if raw_user is not a dict
    if not isinstance(response, MyPlexUser):
        raise TypeError("Plex API returned invalid data.")

    # Return the user
    return response