from typing import Optional

from requests import RequestException, get
from io import BytesIO

from plexapi.myplex import PlexServer, LibrarySection, MyPlexUser, MyPlexAccount, NotFound
from logging import info

from app.models.database import Invitations

from .settings import get_media_settings
from .users import get_users, create_user

from app.models.database.libraries import Libraries

# INDEX OF FUNCTIONS
# - Plex Get Server
# - Plex San Libraries
# - Plex Invite User
# - Plex Get Users
# - Plex Get User
# - Plex Delete User
# - Plex Sync Users

# ANCHOR - Get Plex Server
def get_plex_server(server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> PlexServer:
    """Get a PlexServer object
    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: A PlexServer object
    """

    # Get required settings
    if not server_api_key or not server_url:
        settings = get_media_settings()
        server_url = server_url or settings.get("server_url", None)
        server_api_key = server_api_key or settings.get("server_api_key", None)

    # If server_url does not end with a slash, add one
    if not server_url.endswith("/"):
        server_url = server_url + "/"

    # Create PlexServer object
    plex_server = PlexServer(server_url, server_api_key)

    # Return PlexServer object
    return plex_server


# ANCHOR - Plex Scan Libraries
def scan_plex_libraries(server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> list[LibrarySection]:
    """Scan all Plex libraries
    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str] - If not provided, will get from database.

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


# ANCHOR - Plex Invite User
def invite_plex_user(code: str, token: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None):
    """Invite a user to the Plex server

    :param code: The code of the invitation
    :type code: str

    :param email: The email of the user to invite
    :type email: str

    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Plex Invite
    """

    # Get the PlexServer object
    plex = get_plex_server(server_api_key=server_api_key, server_url=server_url)

    # Get Invitation from Database
    invitation = Invitations.get_or_none(Invitations.code == code)

    sections = None

    # Get sections from invitation
    if invitation.specific_libraries is not None and len(invitation.specific_libraries) > 0:
        sections = [library.name for library in Libraries.filter(Libraries.id.in_(invitation.specific_libraries.split(",")))]

    # Get allow_sync from invitation
    allow_sync = invitation.plex_allow_sync

    # Get my account from Plex
    my_account = plex.myPlexAccount()

    # Get the user from the token
    plex_account = MyPlexAccount(token=token)

    invite_data = {
        "user": plex_account.email,
        "server": plex,
        "allowSync": allow_sync
    }

    if sections:
        invite_data["sections"] = sections

    # Invite the user
    invite = my_account.inviteFriend(**invite_data)

    # If the invite is none raise an error
    if invite is None:
        raise ValueError("Failed to invite user.")

    # Return the invite
    return plex_account


# ANCHOR - Plex Accept Invitation
def accept_plex_invitation(token: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None):
    """Accept a Plex invitation

    :param token: The token of the invitation
    :type token: str

    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: None
    """

    # Get the PlexServer object
    plex = get_plex_server(server_api_key=server_api_key, server_url=server_url)

    # Get my account from Plex and email
    my_account = plex.myPlexAccount()

    # Get plex account for the user
    plex_account = MyPlexAccount(token=token)

    # Accept the invitation and enable sync
    plex_account.acceptInvite(my_account.email)
    plex_account.enableViewStateSync()


# ANCHOR - Plex Get Users
def get_plex_users(server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> list[MyPlexUser]:
    """Get all Plex users
    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str] - If not provided, will get from database.

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
def get_plex_user(user_id: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> MyPlexUser:
    """Get a Plex user
    :param user_id: The id of the user
    :type user_id: str - [usernames, email, id]

    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str] - If not provided, will get from database.

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


# ANCHOR - Delete Plex User
def delete_plex_user(user_id: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None):
    """Delete a Plex user

    :param user_id: The id of the user
    :type user_id: str - [usernames, email, id]

    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: None
    """

    # Get the PlexServer object
    plex = get_plex_server(server_api_key=server_api_key, server_url=server_url)

    # Plex account
    plex_account = plex.myPlexAccount()

    # Delete the user
    try:
        plex_account.removeFriend(user_id)
    except NotFound as e:
        print("NOT IMPORTANT: ", e)
        print("The above error is not important, it just means that the user is not a Plex Friend.")

    try:
        plex_account.removeHomeUser(user_id)
    except NotFound as e:
        print("NOT IMPORTANT: ", e)
        print("The above error is not important, it just means that the user is not a Plex Home User.")


# ANCHOR - Plex Sync Users
def sync_plex_users(server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> list[MyPlexUser]:
    """Sync Plex users
    :param server_api_key: The API key of the Plex server
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: The URL of the Plex server
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: list[dict] - A list of all users
    """

    # Get users from plex
    plex_users = get_plex_users(server_api_key=server_api_key, server_url=server_url)

    # Get users from database
    database_users = get_users(as_dict=False)

    # If plex_users.id is not in database_users.token, add user to database
    for plex_user in plex_users:
        if str(plex_user.id) not in [str(database_user.token) for database_user in database_users]:
            create_user(username=plex_user.title, token=plex_user.id, email=plex_user.email)
            info(f"User {plex_user.title} successfully imported to database")

        # Handle Plex Managed/Guest users.
        # Update DB username to Plex user title.
        # This value is the same as username for normal accounts.
        # For managed accounts without a public username,
        # this value is set to 'Guest' or local username
        elif str(plex_user.username) == "" and plex_user.email is None:
            create_user(username=plex_user.title, token=plex_user.id, email=plex_user.email)
            info(f"Managed User {plex_user.title} successfully updated to database")

    # If database_users.token is not in plex_users.id, remove user from database
    for database_user in database_users:
        if str(database_user.token) not in [str(plex_user.id) for plex_user in plex_users]:
            database_user.delete_instance()
            info(f"User {database_user.username} successfully removed from database")