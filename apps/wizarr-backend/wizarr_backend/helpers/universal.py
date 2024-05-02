from plexapi.myplex import MyPlexUser, NotFound, BadRequest
from requests.exceptions import RequestException
from app.models.jellyfin.user import JellyfinUser
from app.models.emby.user import EmbyUser
from app.extensions import socketio
from datetime import datetime

from .plex import get_plex_users, get_plex_user, sync_plex_users, delete_plex_user, invite_plex_user, accept_plex_invitation
from .jellyfin import get_jellyfin_users, get_jellyfin_user, sync_jellyfin_users, delete_jellyfin_user, invite_jellyfin_user
from .emby import get_emby_users, get_emby_user, sync_emby_users, delete_emby_user, invite_emby_user

from .jellyseerr import jellyseerr_import_user, jellyseerr_delete_user
from .overseerr import overseerr_import_user, overseerr_delete_user
from .ombi import ombi_import_user, ombi_delete_user

from app.models.database.users import Users
from app.models.database.invitations import Invitations
from app.models.database.requests import Requests
from app.models.database.settings import Settings

from helpers.webhooks import run_webhook
from playhouse.shortcuts import model_to_dict

# ANCHOR - Get Server Type
def get_server_type() -> str:
    """Get the server type from the settings

    return: str - [plex, jellyfin]
    """

    # Get the server type from the settings
    server_type = Settings.get_or_none(Settings.key == "server_type").value

    # Raise an error if the server type is not set
    if server_type is None:
        raise ValueError("Server type not set")

    # Return the server type
    return server_type

# ANCHOR - Global Delete User From Request Server
def global_delete_user_from_request_server(user_token: str) -> dict[str]:
    """Delete a user from the request server
    :param user_id: The id of the user
    """

    # Get the requests from the database
    requests = Requests.select()

    # Request Server Map
    universal_delete_user = {
        "jellyseerr": lambda **kwargs: jellyseerr_delete_user(**kwargs),
        "overseerr": lambda **kwargs: overseerr_delete_user(**kwargs),
        "ombi": lambda **kwargs: ombi_delete_user(**kwargs)
    }

    # Loop through the requests server and delete the user
    for request in requests:
        try:
            universal_delete_user.get(request.service)(api_url=request.url, api_key=request.api_key, user_token=user_token)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)

    # Return response
    return { "message": "User deleted from request server" }


# ANCHOR - Global Invite User To Request Server
def global_invite_user_to_request_server(user_token: str) -> dict[str]:
    """Invite a user to the request server
    :param user_id: The id of the user
    """

    # Get the requests from the database
    requests = Requests.select()

    # Request Server Map
    universal_add_user = {
        "jellyseerr": lambda **kwargs: jellyseerr_import_user(**kwargs),
        "overseerr": lambda **kwargs: overseerr_import_user(**kwargs),
        "ombi": lambda **kwargs: ombi_import_user(**kwargs)
    }

    # Loop through the requests server and invite the user
    for request in requests:
        try:
            universal_add_user.get(request.service)(api_url=request.url, api_key=request.api_key, user_token=user_token)
        except Exception as e:
            print(e)

    # Return response
    return { "message": "User invited to request server" }


# ANCHOR - Global Get Users
def global_get_users_from_media_server() -> dict[MyPlexUser or JellyfinUser or EmbyUser]:
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
    elif server_type == "emby":
        users = get_emby_users()

    # Raise an error if the users are None
    if users is None:
        raise ValueError("Unable to get users")

    # Return the users
    return users


# ANCHOR - Global Get User
def global_get_user_from_media_server(user_id: str) -> MyPlexUser or JellyfinUser or EmbyUser:
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
    elif server_type == "emby":
        user = get_emby_user(user_id)

    # Raise an error if the user is None
    if user is None:
        raise ValueError("Unable to get user")

    # Return the user
    return user


# ANCHOR - Global Delete User
def global_delete_user_from_media_server(user_id: str) -> dict[str]:
    """Delete a user from the media server
    :param user_id: The id of the user
    :type user_id: str

    :return: None
    """

    # Get the server type
    server_type = get_server_type()

    # Get the user from the database where the id is equal to the user_id provided
    user = Users.get_or_none(Users.id == user_id)

    # Delete the user from the media server
    if server_type == "plex":
        delete_plex_user(user.token)
    elif server_type == "jellyfin":
        delete_jellyfin_user(user.token)
    elif server_type == "emby":
        delete_emby_user(user.token)

    try:
        # Get the invite from the database where the code is equal to the code provided
        invite: Invitations = Invitations.get_or_none(Invitations.code == user.code)

        # Append the user id to the invite used_by field
        used_by = invite.used_by.split(",") if invite.used_by else []

        # Remove the user id from the used_by field
        used_by.remove(str(user.id))

        # Set the used_by field to the used_by list
        invite.used_by = ",".join(used_by) if len(used_by) > 0 else None

        # Save the invite
        invite.save()
    except Exception as e:
        print(e)

    # Delete the user from the request server
    try:
        global_delete_user_from_request_server(user.token)
    except Exception as e:
        print(e)

    # Send webhook event
    run_webhook("user_deleted", model_to_dict(user))

    # Delete the user from the database
    user.delete_instance()

    # Return response
    return { "message": "User deleted" }


# ANCHOR - Global Sync Users
def global_sync_users_to_media_server() -> dict[str]:
    """Sync users from the media server to the database

    :return: None
    """

    # Get the server type
    server_type = get_server_type()

    # Sync users from the media server to the database
    if server_type == "plex":
        sync_plex_users()

    if server_type == "jellyfin":
        sync_jellyfin_users()

    if server_type == "emby":
        sync_emby_users()

    # Return response
    return { "message": "Users synced" }


# ANCHOR - Global Invite User To Media Server
def global_invite_user_to_media_server(**kwargs) -> dict[str]:
    """Invite a user to the media server

    :param token: The token of the user if Plex
    :type token: str

    :param username: The username of the user if Jellyfin
    :type username: str

    :param email: The email of the user if Jellyfin
    :type email: str

    :param password: The password of the user if Jellyfin
    :type password: str

    :param code: The invite code required for Plex and Jellyfin
    :type code: str

    :return: None
    """

    # Get the server type
    server_type = get_server_type()
    user = None

    # Get the invite from the database where the code is equal to the code provided
    invite: Invitations = Invitations.get_or_none(Invitations.code == kwargs.get("code"))

    # Make sure the invite exists
    if invite is None:
        raise BadRequest("Invalid invite code")

    # Make sure the invite is not expired
    if invite.expires and invite.expires < datetime.utcnow():
        raise BadRequest("Invite code expired")

    # Make sure the invite is not used
    if invite.used and not invite.unlimited:
        raise BadRequest("Invite code already used")

    # Map user creation to there respective functions
    universal_invite_user = {
        "plex": lambda token, code, **kwargs: invite_plex_user(token=token, code=code),
        "jellyfin": lambda username, password, code, **kwargs: invite_jellyfin_user(username=username, password=password, code=code),
        "emby": lambda username, password, code, **kwargs: invite_emby_user(username=username, password=password, code=code)
    }

    # Create a socketio emit function that will emit to the socket_id if it is not None
    socketio_emit = lambda event, data: socketio.emit(event, data, namespace=f"/{server_type}", to=kwargs.get("socket_id")) if kwargs.get("socket_id") else None

    # Emit step 1
    socketio_emit("step", 1)

    # Invite the user to the media server
    try:
        user = universal_invite_user.get(server_type)(**kwargs)
    except BadRequest as e:
        socketio_emit("log", str(e))
        socketio_emit("error", "We were unable to join you to the media server, please try again later.")
        return { "message": "We were unable to join you to the media server, please try again later." }
    except RequestException as e:
        socketio_emit("log", str(e))
        socketio_emit("error", "We were unable to join you to the media server, you may already be a member.")
        return { "message": "We were unable to join you to the media server, you may already be a member." }
    except Exception as e:
        socketio_emit("log", str(e))
        socketio_emit("error", str(e) or "There was issue during the account creation")
        raise BadRequest("There was issue during the account creation") from e

    # Emit step 2
    socketio_emit("step", 2)

    try:
        if server_type == "plex": accept_plex_invitation(token=kwargs.get("token"))
    except NotFound as e:
        socketio_emit("log", str(e))
        socketio_emit("error", "We were unable to accept the Plex Invite on your behalf, please accept the invite manually through Plex or your email.")
        return { "message": "We were unable to accept the Plex Invite on your behalf, please accept the invite manually through Plex or your email." }
    except Exception as e:
        socketio_emit("log", str(e))
        socketio_emit("error", str(e) or "There was issue during the account invitation")
        raise BadRequest("There was issue during the account invitation") from e

    # Emit step 3
    socketio_emit("step", 3)

    # Raise an error if the invite is None
    if not user:
        socketio_emit("error", "We were unable to locate your Plex account, please try again later.")
        return { "message": "We were unable to locate your Plex account, please try again later." }

    try:
        # Create the user in the database
        db_user = Users.insert({
            Users.token: user.id if server_type == "plex" else user["Id"],
            Users.username: user.username if server_type == "plex" else user["Name"],
            Users.code: invite.code,
            Users.expires: invite.duration,
            Users.auth: kwargs.get("token", None),
            Users.email: user.email if server_type == "plex" else kwargs.get("email", None),
            Users.created: datetime.utcnow()
        })

        # Add the user to the database
        # pylint: disable=no-value-for-parameter
        user_id = db_user.execute()
    except Exception as e:
        socketio_emit("log", str(e))
        socketio_emit("error", str(e) or "There was issue during local account creation")
        raise BadRequest("There was issue during local account creation") from e


    try:
        # Send webhook event
        run_webhook("user_invited", model_to_dict(
            Users.get_or_none(Users.id == user_id)
        ))
    except Exception as e:
        socketio_emit("log", str(e))
        print(e)

    try:
        global_invite_user_to_request_server(user_token=user.id if server_type == "plex" else user["Id"])
    except Exception as e:
        socketio_emit("log", str(e))
        print(e)

    try:
        # Set the invite to used
        invite.used = True
        invite.used_at = datetime.now()

        # Append the user id to the invite used_by field
        used_by = invite.used_by.split(",") if invite.used_by else []

        # Append the user id to the used_by field if it is not already in there
        if str(user_id) not in used_by:
            used_by.append(str(user_id))

        # Set the used_by field to the used_by list
        invite.used_by = ",".join(used_by) if len(used_by) > 0 else None

        # Save the invite
        invite.save()
    except Exception as e:
        socketio_emit("log", str(e))
        print(e)

    # Emit done
    socketio_emit("done", None)

    # Return response
    return { "message": "User invited to media server", "invite": invite, "user": db_user }
