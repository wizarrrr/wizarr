from typing import Optional

from requests import RequestException, get, post, delete
from logging import info
from io import BytesIO

from app.models.database import Invitations

from .settings import get_media_settings
from .users import get_users, create_user, get_user_by_token

from app.models.emby.user import EmbyUser
from app.models.emby.user_policy import EmbyUserPolicy
from app.models.emby.library import EmbyLibraryItem

# INDEX OF FUNCTIONS
# - Emby Get Request
# - Emby Post Request
# - Emby Delete Request
# - Emby Scan Libraries
# - Emby Get Policy
# - Emby Invite User
# - Emby Get Users
# - Emby Get User
# - Emby Delete User
# - Emby Sync Users

# ANCHOR - Emby Get Request
def get_emby(api_path: str, as_json: Optional[bool] = True, server_api_key: Optional[str] = None, server_url: Optional[str] = None):
    """Get data from Emby.
    :param api_path: API path to get data from
    :type api_path: str

    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Emby API response
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

    # Add api_path to Emby URL
    api_url = str(server_url) + api_path

    # Set headers for Emby API
    headers = {
        "X-Emby-Token": server_api_key,
        "Accept": "application/json, profile=\"PascalCase\""
    }

    # Get data from Emby
    response = get(url=api_url, headers=headers, timeout=30)

    # Raise exception if Emby API returns non-2** status code
    if not response.ok:
        raise RequestException(
            f"Emby API returned {response.status_code} status code."
        )

    # Return response
    if as_json:
        return response.json() if response.content else None
    else:
        return response if response.content else None


# ANCHOR - Emby Post Request
def post_emby(api_path: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None, json: Optional[dict] = None, data: Optional[any] = None):
    """Post data to Emby.
    :param api_path: API path to post data to
    :type api_path: str

    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :param data: Data to post to Emby
    :type data: Optional[dict]

    :return: Emby API response
    """

    # Get required settings
    if not server_api_key or not server_url:
        settings = get_media_settings()
        server_url = server_url or settings.get("server_url", None)
        server_api_key = server_api_key or settings.get("server_api_key", None)

    # Add api_path to Emby URL
    api_url = str(server_url) + api_path

    # Set headers for Emby API
    headers = {
        "X-Emby-Token": server_api_key,
        "Accept": "application/json"
    }

    # Post data to Emby
    response = post(url=api_url, headers=headers, data=data, json=json, timeout=30)

    # Raise exception if Emby API returns non-2** status code
    if not response.ok:
        raise RequestException(
            f"Emby API returned {response.status_code} status code."
        )

    response.raise_for_status()

    return response.json() if response.content else None


# ANCHOR - Emby Delete Request
def delete_emby(api_path: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> None:
    """Delete data from Emby.
    :param api_path: API path to delete data from
    :type api_path: str

    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: None
    """

    # Get required settings
    if not server_api_key or not server_url:
        settings = get_media_settings()
        server_url = server_url or settings.get("server_url", None)
        server_api_key = server_api_key or settings.get("server_api_key", None)

    # Add api_path to Emby URL
    api_url = str(server_url) + api_path

    # Set headers for Emby API
    headers = {
        "X-Emby-Token": server_api_key,
        "Accept": "application/json, profile=\"PascalCase\""
    }

    # Delete data from Emby
    response = delete(url=api_url, headers=headers, timeout=30)

    # Raise exception if Emby API returns non-2** status code
    if not response.ok:
        raise RequestException(
            f"Emby API returned {response.status_code} status code."
        )

    return response.json() if response.content else None


# ANCHOR - Emby Scan Libraries
def scan_emby_libraries(server_api_key: Optional[str], server_url: Optional[str]) -> list[EmbyLibraryItem]:
    """Scan Emby libraries and return list of libraries.
    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: List of libraries
    """

    # Get libraries from Emby
    response = get_emby(
        api_path="/Library/MediaFolders", server_api_key=server_api_key, server_url=server_url
    )

    # Check if items exist
    if response["Items"] is None:
        raise ValueError("No libraries found.")

    # Return list of libraries
    return response["Items"]


# ANCHOR - Emby Get Policy
def get_emby_policy(user_id: str, server_api_key: Optional[str], server_url: Optional[str]) -> EmbyUserPolicy:
    """Get policy from Emby.

    :param user_id: ID of the user to get policy for
    :type user_id: str

    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Emby API response
    """

    # Get user from Emby
    response = get_emby(
        api_path=f"/Users/{user_id}", server_api_key=server_api_key, server_url=server_url
    )

    # Check if user has a policy
    if response["Policy"] is None:
        raise ValueError("User does not have a policy.")

    return response["Policy"]


# ANCHOR - Emby Invite User
def invite_emby_user(username: str, password: str, code: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> EmbyUser:
    """Invite user to Emby.

    :param username: Username of the user to invite
    :type username: str

    :param password: Password of the user to invite
    :type password: str

    :param code: Invitation code
    :type code: str

    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Emby API response
    """

    # Get Invitation from Database
    invitation = Invitations.get_or_none(Invitations.code == code)

    sections = None

    # Get libraries from invitation
    if invitation.specific_libraries is not None and len(invitation.specific_libraries) > 0:
        sections = invitation.specific_libraries.split(",")

    # Create user object
    new_user = { "Name": str(username) }

    # Create user in Emby
    user_response = post_emby(api_path="/Users/New", json=new_user, server_api_key=server_api_key, server_url=server_url)

    # Create policy object
    new_policy = {
        "EnableAllFolders": True,
        "SimultaneousStreamLimit": 0,
        "EnableLiveTvAccess": False,
        "EnableLiveTvManagement": False,
        "AuthenticationProviderId": "Emby.Server.Implementations.Library.DefaultAuthenticationProvider",
    }

    # Set library options
    if sections:
        new_policy["EnableAllFolders"] = False
        new_policy["EnabledFolders"] = sections

    # Set stream limit options
    if invitation.sessions is not None and int(invitation.sessions) > 0:
        new_policy["SimultaneousStreamLimit"] = int(invitation.sessions)

    # Set live tv access
    if invitation.live_tv is not None and invitation.live_tv == True:
        new_policy["EnableLiveTvAccess"] = True

    # Set the hidden user status
    if invitation.hide_user is not None and invitation.hide_user == False:
        new_policy["IsHiddenRemotely"] = False

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
    post_emby(api_path=api_path, json=new_policy, server_api_key=server_api_key, server_url=server_url)

    # Set user password, this is done after the policy is set due to LDAP policies
    post_emby(api_path=f"/Users/{user_response['Id']}/Password", json={"NewPw": str(password)}, server_api_key=server_api_key, server_url=server_url)

    # Return response
    return user_response


# ANCHOR - Emby Get Users
def get_emby_users(server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> list[EmbyUser]:
    """Get users from Emby.

    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Emby API response
    """

    # Get users from Emby
    response = get_emby(api_path="/Users", server_api_key=server_api_key, server_url=server_url)

    # Return users
    return response


# ANCHOR - Emby Get User
def get_emby_user(user_id: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> EmbyUser:
    """Get user from Emby.

    :param user_id: ID of the user to get
    :type user_id: str

    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: Emby API response
    """

    # Get user from Emby
    response = get_emby(api_path=f"/Users/{user_id}", server_api_key=server_api_key, server_url=server_url)

    # Return user
    return response


# ANCHOR - Emby Delete User
def delete_emby_user(user_id: str, server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> None:
    """Delete user from Emby.
    :param user_id: ID of the user to delete
    :type user_id: str

    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: None
    """

    # Delete user from Emby
    delete_emby(api_path=f"/Users/{user_id}", server_api_key=server_api_key, server_url=server_url)


# ANCHOR - Emby Sync Users
def sync_emby_users(server_api_key: Optional[str] = None, server_url: Optional[str] = None) -> list[EmbyUser]:
    """Sync users from Emby to database.

    :param server_api_key: Emby API key
    :type server_api_key: Optional[str] - If not provided, will get from database.

    :param server_url: Emby URL
    :type server_url: Optional[str] - If not provided, will get from database.

    :return: None
    """

    # Get users from Emby
    emby_users = get_emby_users(server_api_key=server_api_key, server_url=server_url)

    # Get users from database
    database_users = get_users(False)

    # If emby_users.id not in database_users.token, add to database
    for emby_user in emby_users:
        if str(emby_user["Id"]) not in [str(database_user.token) for database_user in database_users]:
            # Check to see if user has a connect username, if not set to None
            email = emby_user["ConnectUserName"] if "ConnectUserName" in emby_user else None
            create_user(username=emby_user["Name"], token=emby_user["Id"], email=email)
            info(f"User {emby_user['Name']} successfully imported to database.")

        # If the user does exist then update their username and email if it has changed
        else:
            user = get_user_by_token(emby_user["Id"], verify=False)
            email = emby_user["ConnectUserName"] if "ConnectUserName" in emby_user else None
            if (emby_user["Name"] != user.username or (email is not None and email != user.email)):
                user.username = emby_user["Name"]
                user.email = email
                user.save()
                info(f"User {emby_user['Name']} successfully updated in database.")

    # If database_users.token not in emby_users.id, delete from database
    for database_user in database_users:
        if str(database_user.token) not in [str(emby_user["Id"]) for emby_user in emby_users]:
            database_user.delete_instance()
            info(f"User {database_user.username} successfully deleted from database.")