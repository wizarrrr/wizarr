from typing import Optional

from plexapi.myplex import PlexServer, LibrarySection, MyPlexUser
from pydantic import HttpUrl
from logging import info

from .settings import get_settings
from .users import get_users, create_user

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
    plex = get_plex_server(server_api_key=server_api_key, server_url=server_url)

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
    plex = get_plex_server(server_api_key=server_api_key, server_url=server_url)

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
    plex = get_plex_server(server_api_key=server_api_key, server_url=server_url)

    # Get the raw user
    response: MyPlexUser = plex.myPlexAccount().user(user_id)

    # Raise exception if raw_user is not a dict
    if not isinstance(response, MyPlexUser):
        raise TypeError("Plex API returned invalid data.")

    # Return the user
    return response


# ANCHOR - Plex Sync Users
def sync_plex_users(server_api_key: Optional[str] = None, server_url: Optional[str or HttpUrl] = None) -> list[MyPlexUser]:
    """Sync Plex users
    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str or HttpUrl] - If not provided, will get from database.

    :return: list[dict] - A list of all users
    """

    # Get users from plex
    plex_users = get_plex_users(server_api_key=server_api_key, server_url=server_url)

    # Get users from database
    database_users = get_users()

    # If plex_users.id is not in database_users.token, add user to database
    for plex_user in plex_users:
        if plex_user.id not in [database_user.token for database_user in database_users]:
            create_user(username=plex_user.username, token=plex_user.id, email=plex_user.email)
            info(f"User {plex_user.username} successfully imported to database")


    # If database_users.token is not in plex_users.id, remove user from database
    for database_user in database_users:
        if database_user.token not in [plex_user.id for plex_user in plex_users]:
            database_user.delete_instance()
            info(f"User {database_user.username} successfully removed from database")

    # Return the users
    return get_plex_users(server_api_key=server_api_key, server_url=server_url)