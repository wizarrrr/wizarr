from plexapi.myplex import MyPlexUser, NotFound, BadRequest
from models.jellyfin.user import JellyfinUser
from app.extensions import socketio

from .settings import get_setting
from .plex import get_plex_users, get_plex_user, sync_plex_users, delete_plex_user, get_plex_profile_picture, invite_plex_user, accept_plex_invitation
from .jellyfin import get_jellyfin_users, get_jellyfin_user, sync_jellyfin_users, delete_jellyfin_user, get_jellyfin_profile_picture, invite_jellyfin_user

from models.database.users import Users

# ANCHOR - Get Server Type
def get_server_type() -> str:
    """Get the server type from the settings

    return: str - [plex, jellyfin]
    """

    # Get the server type from the settings
    server_type = get_setting("server_type")

    # Raise an error if the server type is not set
    if server_type is None:
        raise ValueError("Server type not set")

    # Return the server type
    return server_type


# ANCHOR - Global Get Users
def global_get_users() -> dict[MyPlexUser or JellyfinUser]:
    """Get all users from the media server

    :return: A list of users
    """

    # Get the server type and set the users variable
    server_type = get_server_type()
    users = None

    # Get the users from the media server
    if server_type == "plex":
        users = get_plex_users()
    elif server_type == "jellyfin":
        users = get_jellyfin_users()

    # Raise an error if the users are None
    if users is None:
        raise ValueError("Unable to get users")

    # Return the users
    return users


# ANCHOR - Global Get User
def global_get_user(user_id: str) -> MyPlexUser or JellyfinUser:
    """Get a user from the media server
    :param user_id: The id of the user
    :type user_id: str

    :return: A user
    """

    # Get the server type and set the user variable
    server_type = get_server_type()
    user = None

    # Get the user from the media server
    if server_type == "plex":
        user = get_plex_user(user_id)
    elif server_type == "jellyfin":
        user = get_jellyfin_user(user_id)

    # Raise an error if the user is None
    if user is None:
        raise ValueError("Unable to get user")

    # Return the user
    return user


# ANCHOR - Global Delete User
def global_delete_user(user_id: str) -> dict[str]:
    """Delete a user from the media server
    :param user_id: The id of the user
    :type user_id: str

    :return: None
    """

    # Get the server type
    server_type = get_server_type()

    # Delete the user from the media server
    if server_type == "plex":
        delete_plex_user(user_id)
    elif server_type == "jellyfin":
        delete_jellyfin_user(user_id)

    # Delete the user from the database
    Users.delete().where(Users.token == user_id).execute()

    # Return response
    return { "message": "User deleted" }


# ANCHOR - Global Sync Users
def global_sync_users() -> dict[str]:
    """Sync users from the media server to the database

    :return: None
    """

    # Get the server type
    server_type = get_server_type()

    # Sync users from the media server to the database
    if server_type == "plex":
        sync_plex_users()
    elif server_type == "jellyfin":
        sync_jellyfin_users()

    # Return response
    return { "message": "Users synced" }


# ANCHOR - Global Get User Profile Picture
def global_get_user_profile_picture(user_id: str) -> str:
    """Get a user"s profile picture from the media server

    :param user_id: The id of the user
    :type user_id: str

    :return: The url of the user"s profile picture
    """

    # Get the server type
    server_type = get_server_type()

    # Get the user"s profile picture from the media server
    if server_type == "plex":
        return get_plex_profile_picture(user_id)
    elif server_type == "jellyfin":
        return get_jellyfin_profile_picture(user_id)

    # Raise an error if the user"s profile picture is None
    raise ValueError("Unable to get user's profile picture")


# ANCHOR - Global Invite User To Media Server
def global_invite_user_to_media_server(**kwargs) -> dict[str]:
    """Invite a user to the media server

    :param token: The token of the user if Plex
    :type token: str

    :param username: The username of the user if Jellyfin
    :type username: str

    :param password: The password of the user if Jellyfin
    :type password: str

    :param code: The invite code required for Plex and Jellyfin
    :type code: str

    :return: None
    """

    # Get the server type
    server_type = get_server_type()
    invite = None

    # If socket_id is not None, emit step 1
    if kwargs.get("socket_id"):
        socketio.emit("step", 1, namespace="/plex", to=kwargs.get("socket_id"))

    # Invite the user to the media server
    if server_type == "plex":
        try:
            invite = invite_plex_user(token=kwargs.get("token"), code=kwargs.get("code"))
        except BadRequest:
            if kwargs.get("socket_id"):
                socketio.emit("error", "You maybe, already a member of this server.", namespace="/plex", to=kwargs.get("socket_id"))
    elif server_type == "jellyfin":
        invite = invite_jellyfin_user(username=kwargs.get("username"), password=kwargs.get("password"), code=kwargs.get("code"))

    # If socket_id is not None, emit step 1
    if kwargs.get("socket_id"):
        socketio.emit("step", 2, namespace="/plex", to=kwargs.get("socket_id"))

    if server_type == "plex":
        try:
            accept_plex_invitation(token=kwargs.get("token"))
        except NotFound:
            if kwargs.get("socket_id"):
                socketio.emit("error", "Could not accept Plex Invite", namespace="/plex", to=kwargs.get("socket_id"))
        except Exception as e:
            if kwargs.get("socket_id"):
                socketio.emit("error", e.message, namespace="/plex", to=kwargs.get("socket_id"))

    # If socket_id is not None, emit step 1
    if kwargs.get("socket_id"):
        socketio.emit("step", 3, namespace="/plex", to=kwargs.get("socket_id"))

    # Raise an error if the invite is None
    if invite is None:
        raise ValueError("Unable to invite user to media server")

    # Return response
    return { "message": "User invited to media server", "invite": invite }

