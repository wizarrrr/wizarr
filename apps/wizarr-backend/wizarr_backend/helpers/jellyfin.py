from typing import Optional

from requests import RequestException, get, post, delete
from logging import info
from io import BytesIO

from app.models.database import Invitations

from .settings import get_media_settings
from .users import get_users, create_user, get_user_by_token

from app.models.jellyfin.user import JellyfinUser
from app.models.jellyfin.user_policy import JellyfinUserPolicy
from app.models.jellyfin.library import JellyfinLibraryItem

# INDEX OF FUNCTIONS
# - Jellyfin Get Request
# - Jellyfin Post Request
# - Jellyfin Delete Request
# - Jellyfin Scan Libraries
# - Jellyfin Get Policy
# - Jellyfin Invite User
# - Jellyfin Get Users
# - Jellyfin Get User
# - Jellyfin Delete User
# - Jellyfin Sync Users

# ANCHOR - Jellyfin Get Request
def get_jellyfin(api_path: str, as_json: Optional[bool] = True, server_api_key: Optional[str] = None, server_url: Optional[str] = None):
    """Get data from Jellyfin.
    :param api_path: API path to get data from
    :type api_path: str

    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Jellyfin API response
    """

    # Get required settings
    if not server_api_key or not server_url:
        settings = get_media_settings()
        server_url = server_url or settings.get("server_url", None)
        server_api_key = server_api_key or settings.get("server_api_key", None)

    # If server_url does not end with a slash, add one
    if not server_url.endswith("/"):
        server_url = server_url + "/"

    # If api_path starts with a slash, remove it
    if api_path.startswith("/"):
        api_path = api_path[1:]

    # Add api_path to Jellyfin URL
    api_url = str(server_url) + api_path

    # Set headers for Jellyfin API
    headers = {
        "X-Emby-Token": server_api_key,
        "Accept": "application/json, profile=\"PascalCase\""
    }

    # Get data from Jellyfin
    response = get(url=api_url, headers=headers, timeout=30)

    # Raise exception if Jellyfin API returns non-2** status code
    if not response.ok:
        raise RequestException(
            f"Jellyfin API returned {response.status_code} status code."
        )

    # Return response
    if as_json:
        return response.json() if response.content else None
    else:
        return response if response.content else None


# ANCHOR - Jellyfin Post Request
def post_jellyfin(api_path: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None, json: Optional[dict] = None, data: Optional[any] = None):
    """Post data to Jellyfin.
    :param api_path: API path to post data to
    :type api_path: str

    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :param data: Data to post to Jellyfin
    :type data: Optional[dict]

    :return: Jellyfin API response
    """

    # Get required settings
    if not server_api_key or not server_url:
        settings = get_media_settings()
        server_url = server_url or settings.get("server_url", None)
        server_api_key = server_api_key or settings.get("server_api_key", None)

    # Add api_path to Jellyfin URL
    api_url = str(server_url) + api_path

    # Set headers for Jellyfin API
    headers = {
        "X-Emby-Token": server_api_key,
        "Accept": "application/json"
    }

    # Post data to Jellyfin
    response = post(url=api_url, headers=headers, data=data, json=json, timeout=30)

    # Raise exception if Jellyfin API returns non-2** status code
    if not response.ok:
        raise RequestException(
            f"Jellyfin API returned {response.status_code} status code."
        )

    response.raise_for_status()

    return response.json() if response.content else None


# ANCHOR - Jellyfin Delete Request
def delete_jellyfin(api_path: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> None:
    """Delete data from Jellyfin.
    :param api_path: API path to delete data from
    :type api_path: str

    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: None
    """

    # Get required settings
    if not server_api_key or not server_url:
        settings = get_media_settings()
        server_url = server_url or settings.get("server_url", None)
        server_api_key = server_api_key or settings.get("server_api_key", None)

    # Add api_path to Jellyfin URL
    api_url = str(server_url) + api_path

    # Set headers for Jellyfin API
    headers = {
        "X-Emby-Token": server_api_key,
        "Accept": "application/json, profile=\"PascalCase\""
    }

    # Delete data from Jellyfin
    response = delete(url=api_url, headers=headers, timeout=30)

    # Raise exception if Jellyfin API returns non-2** status code
    if not response.ok:
        raise RequestException(
            f"Jellyfin API returned {response.status_code} status code."
        )

    return response.json() if response.content else None


# ANCHOR - Jellyfin Scan Libraries
def scan_jellyfin_libraries(server_api_key: Optional[str], server_url: Optional[str]) -> list[JellyfinLibraryItem]:
    """Scan Jellyfin libraries and return list of libraries.
    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: List of libraries
    """

    # Get libraries from Jellyfin
    response = get_jellyfin(
        api_path="/Library/MediaFolders", server_api_key=server_api_key, server_url=server_url
    )

    # Check if items exist
    if response["Items"] is None:
        raise ValueError("No libraries found.")

    # Return list of libraries
    return response["Items"]


# ANCHOR - Jellyfin Get Policy
def get_jellyfin_policy(user_id: str, server_api_key: Optional[str], server_url: Optional[str]) -> JellyfinUserPolicy:
    """Get policy from Jellyfin.

    :param user_id: ID of the user to get policy for
    :type user_id: str

    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Jellyfin API response
    """

    # Get user from Jellyfin
    response = get_jellyfin(
        api_path=f"/Users/{user_id}", server_api_key=server_api_key, server_url=server_url
    )

    # Check if user has a policy
    if response["Policy"] is None:
        raise ValueError("User does not have a policy.")

    return response["Policy"]


# ANCHOR - Jellyfin Invite User
def invite_jellyfin_user(username: str, password: str, code: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> JellyfinUser:
    """Invite user to Jellyfin.

    :param username: Username of the user to invite
    :type username: str

    :param password: Password of the user to invite
    :type password: str

    :param code: Invitation code
    :type code: str

    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Jellyfin API response
    """

    # Get Invitation from Database
    invitation = Invitations.get_or_none(Invitations.code == code)

    sections = None

    # Get libraries from invitation
    if invitation.specific_libraries is not None and len(invitation.specific_libraries) > 0:
        sections = invitation.specific_libraries.split(",")

    # Create user object
    new_user = { "Name": str(username), "Password": str(password) }

    # Create user in Jellyfin
    user_response = post_jellyfin(api_path="/Users/New", json=new_user, server_api_key=server_api_key, server_url=server_url)

    # Create policy object
    new_policy = {
        "EnableAllFolders": True,
        "MaxActiveSessions": 0,
        "EnableLiveTvAccess": False,
        "EnableLiveTvManagement": False,
        "AuthenticationProviderId": "Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider",
    }

    # Set library options
    if sections:
        new_policy["EnableAllFolders"] = False
        new_policy["EnabledFolders"] = sections

    # Set session limit options
    if invitation.sessions is not None and int(invitation.sessions) > 0:
        new_policy["MaxActiveSessions"] = int(invitation.sessions)

    # Set live tv access
    if invitation.live_tv is not None and invitation.live_tv == True:
        new_policy["EnableLiveTvAccess"] = True

    # Set the hidden user status
    if invitation.hide_user is not None and invitation.hide_user == False:
        new_policy["IsHidden"] = False

    # Set the Allow Download status
    if invitation.allow_download is not None and invitation.allow_download == False:
        new_policy["EnableContentDownloading"] = False

    # Get users default policy
    old_policy = user_response["Policy"]

    # Merge policy with user policy don't overwrite
    new_policy = {**old_policy, **new_policy}

    # API path fpr user policy
    api_path = f"/Users/{user_response['Id']}/Policy"

    # Update user policy
    post_jellyfin(api_path=api_path, json=new_policy, server_api_key=server_api_key, server_url=server_url)

    # Return response
    return user_response


# ANCHOR - Jellyfin Get Users
def get_jellyfin_users(server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> list[JellyfinUser]:
    """Get users from Jellyfin.

    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Jellyfin API response
    """

    # Get users from Jellyfin
    response = get_jellyfin(api_path="/Users", server_api_key=server_api_key, server_url=server_url)

    # Return users
    return response


# ANCHOR - Jellyfin Get User
def get_jellyfin_user(user_id: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> JellyfinUser:
    """Get user from Jellyfin.

    :param user_id: ID of the user to get
    :type user_id: str

    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Jellyfin API response
    """

    # Get user from Jellyfin
    response = get_jellyfin(api_path=f"/Users/{user_id}", server_api_key=server_api_key, server_url=server_url)

    # Return user
    return response


# ANCHOR - Jellyfin Delete User
def delete_jellyfin_user(user_id: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> None:
    """Delete user from Jellyfin.
    :param user_id: ID of the user to delete
    :type user_id: str

    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: None
    """

    # Delete user from Jellyfin
    delete_jellyfin(api_path=f"/Users/{user_id}", server_api_key=server_api_key, server_url=server_url)


# ANCHOR - Jellyfin Sync Users
def sync_jellyfin_users(server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> list[JellyfinUser]:
    """Sync users from Jellyfin to database.

    :param server_api_key: Jellyfin API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Jellyfin URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: None
    """

    # Get users from Jellyfin
    jellyfin_users = get_jellyfin_users(server_api_key=server_api_key, server_url=server_url)

    # Get users from database
    database_users = get_users(False)

    # If jellyfin_users.id not in database_users.token, add to database
    for jellyfin_user in jellyfin_users:
        if str(jellyfin_user["Id"]) not in [str(database_user.token) for database_user in database_users]:
            create_user(username=jellyfin_user["Name"], token=jellyfin_user["Id"])
            info(f"User {jellyfin_user['Name']} successfully imported to database.")

        # If database_users.token in jellyfin_users.id, update the users name in database
        else:
            user = get_user_by_token(jellyfin_user["Id"], verify=False)

            if (jellyfin_user["Name"] != user.username):
                user.username = jellyfin_user["Name"]
                user.save()
                info(f"User {jellyfin_user['Name']} successfully updated in database.")

    # If database_users.token not in jellyfin_users.id, delete from database
    for database_user in database_users:
        if str(database_user.token) not in [str(jellyfin_user["Id"]) for jellyfin_user in jellyfin_users]:
            database_user.delete_instance()
            info(f"User {database_user.username} successfully deleted from database.")