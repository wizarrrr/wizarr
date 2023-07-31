import datetime
import threading
from logging import error, info, warning, webpush

from cachetools import TTLCache, cached
from flask import abort, jsonify, request
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin, PlexServer

from app import app, scheduler
from app.mediarequest import *
from app.notifications import notify
from models.database import Invitations, Libraries, Settings, Users

# INVITE USER TO PLEX SERVER
# UPDATE OR CREATE USER IN DATABASE
# PLEX SETUP USER

def plex_handle_oauth_token(token, code):
    email = MyPlexAccount(token).email
    plex_invite_user(email, code)
    # if Users.select().where(Users.email == email).exists():
    #     Users.delete().where(Users.email == email).execute()
    # expires = datetime.datetime.now() + datetime.timedelta(days=int(Invitations.get(code=code).duration)
    #                                                        ) if Invitations.get(code=code).duration else None
    # user = Users.create(token=MyPlexAccount(token).id, email=email,
    #                     username=MyPlexAccount(token).username, code=code, expires=expires, auth=token)
    # notify("User Joined", f"User {MyPlexAccount(token).username} has joined your server!", "tada")
    # user.save()
    # threading.Thread(target=plex_setup_user, args=(token,)).start()

def plex_get_user(user):
    email = Users.get_by_id(user).email
    plex_token = Settings.get(Settings.key == "server_api_key").value
    admin = MyPlexAccount(plex_token)

    my_plex_user = admin.user(email)
    user = {
        "Name": my_plex_user.title,
        "Id": my_plex_user.id,
        "Configuration": {
            "allowCameraUpload": my_plex_user.allowCameraUpload,
            "allowChannels": my_plex_user.allowChannels,
            "allowSync": my_plex_user.allowSync,
        },
        "Policy": {
            "sections": "na"
        }
    }

    return user


@cached(cache=TTLCache(maxsize=1024, ttl=600))
def plex_get_users():
    token = Settings.get(Settings.key == "server_api_key").value
    admin = MyPlexAccount(token)
    plexusers = admin.users()
    # Compare database to users

    for user in plexusers:
        if not user.email:
            user.email = "None"
        if not Users.select().where(Users.username == user.title).exists():
            Users.create(email=user.email, username=user.title,
                         token=user.id, code="None")
            info(f"Added {user.title} to database")

    if Users.select():
        for dbuser in Users.select():
            if dbuser.username not in [u.title for u in plexusers]:
                dbuser.delete_instance()
    users = Users.select()
    for user in users:
        user.expires = Users.get_or_none(Users.email == str(
            user.email)).expires if Users.get_or_none(Users.email == str(user.email)) else None
        user.code = Users.get_or_none(Users.email == str(
            user.email)).code if Users.get_or_none(Users.email == str(user.email)) else None
        for plexuser in plexusers:
            if user.email == plexuser.email:
                user.photo = plexuser.thumb

    return users


def plex_delete_user(id):
    plex_get_users.cache_clear()
    email = Users.get(Users.id == id).email
    if email != "None":
        plex_token = Settings.get(Settings.key == "server_api_key").value
        admin = MyPlexAccount(plex_token)
        try:
            admin.removeHomeUser(email)
        except:
            admin.removeFriend(email)
    return


def plex_invite_user(email, code, sse: ServerSentEvents = None, sse_id: str = None):
    # Get settings from database and invitation from database
    settings = { setting.key: setting.value for setting in Settings.select() }
    invitation: Invitations = Invitations.select().where(Invitations.code == code).first()

    # If invitation does not exist, raise exception
    if not invitation:
        if sse: sse.send("Invitation does not exist", sse_id, "error")
        raise Exception("Invitation does not exist")

    # Clear plex_get_users cache
    plex_get_users.cache_clear()

    # Get server_url and server_api_key from settings dictonary
    server_url = settings.get("server_url", None)
    server_api_key = settings.get("server_api_key", None)

    # Create plex_server object
    plex_server = PlexServer(server_url, server_api_key)

    # Get libraries from database
    libraries = [{"id": library.id, "name": library.name} for library in Libraries.select()]

    # Get sections from libraries.name if invitation.specific_libraries is None, else get from invitation.specific_libraries and split by ", "
    sections = [library["name"] for library in libraries if not invitation.specific_libraries or library["id"] in invitation.specific_libraries.split(",")]

    # Get allow_sync and plex_home from invitation
    allow_sync = invitation.plex_allow_sync
    plex_home = invitation.plex_home

    # Get myPlexAccount object
    my_plex_account = plex_server.myPlexAccount()

    # SSE step 1
    if sse: sse.send(1, sse_id, "step")

    # Select method to invite user based on plex_home
    invite = my_plex_account.createHomeUser if plex_home else my_plex_account.inviteFriend

    # Invite user to plex server
    try:
        invite(user=email, server=plex_server, sections=sections, allowSync=allow_sync)
    except Exception as e:
        if sse: sse.send("Failed to invite user", sse_id, "error")
        info("Failed to invite user: " + str(e))
        raise Exception("Failed to invite user")

    info("Invited " + email + " to Plex Server")

    # if Invitations.select().where(Invitations.code == code, Invitations.unlimited == 0):
    #     Invitations.update(used=True, used_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()
    # else:
    #     Invitations.update(used_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()


def plex_setup_user(token):
    try:
        plex_get_users.cache_clear()
        plex_token = Settings.get(Settings.key == "server_api_key").value
        admin_email = MyPlexAccount(plex_token).email
        user = MyPlexAccount(token)
        user.acceptInvite(admin_email)
        user.enableViewStateSync()
        mediarequest_import_users([user.id])
    except Exception as e:
        error("Failed to setup user: " + str(e))




def plex_opt_out_online_sources(token):
    user = MyPlexAccount(token)
    for source in user.onlineMediaSources():
        source.optOut()
    return


# @app.route('/scan', methods=["POST"])
# def plex_scan():
#     plex_url = request.args.get('plex_url')
#     plex_token = request.args.get('plex_token')
#     if not plex_url or not plex_token:
#         abort(400)
#     try:
#         plex = PlexServer(plex_url, token=plex_token)
#         libraries_raw = plex.library.sections()
#     except:
#         abort(400)
#     libraries = []
#     for library in libraries_raw:
#         libraries.append(library.title)
#     return jsonify(libraries)


# @app.route('/scan-specific', methods=["POST"])
# def plex_scan_specific():
#     plex_url = Settings.get(Settings.key == "server_url").value
#     plex_token = Settings.get(Settings.key == "server_api_key").value
#     if not plex_url or not plex_token:
#         abort(400)
#     try:
#         plex = PlexServer(plex_url, token=plex_token)
#         libraries_raw = plex.library.sections()
#     except:
#         abort(400)
#     libraries = []
#     for library in libraries_raw:
#         libraries.append(library.title)
#     return jsonify(libraries)
