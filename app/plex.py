from plexapi.myplex import MyPlexPinLogin, MyPlexAccount, PlexServer
from app import app, Invitations, Settings, Users, scheduler
from app.notifications import notify
import datetime
import os
import threading
from flask import request, abort, jsonify
import logging
from cachetools import cached, TTLCache 
from app.mediarequest import *


def plex_handle_oauth_token(token, code):
    email = MyPlexAccount(token).email
    plex_invite_user(email, code)
    if Users.select().where(Users.email == email).exists():
        Users.delete().where(Users.email == email).execute()
    expires = datetime.datetime.now() + datetime.timedelta(days=int(Invitations.get(code=code).duration)
                                                           ) if Invitations.get(code=code).duration else None
    user = Users.create(token=MyPlexAccount(token).id, email=email,
                        username=MyPlexAccount(token).username, code=code, expires=expires, auth=token)
    notify("User Joined", f"User {MyPlexAccount(token).username} has joined your server!", "tada")
    user.save()
    threading.Thread(target=plex_setup_user, args=(token,)).start()


def plex_get_user(user):
    print("user is ", user)
    email = Users.get_by_id(user).email
    plex_token = Settings.get(Settings.key == "api_key").value
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
    token = Settings.get(Settings.key == "api_key").value
    admin = MyPlexAccount(token)
    plexusers = admin.users()
    # Compare database to users

    for user in plexusers:
        if not user.email:
            user.email = "None"
        if not Users.select().where(Users.username == user.title).exists():
            Users.create(email=user.email, username=user.title,
                         token=user.id, code="None")
            logging.info(f"Added {user.title} to database")

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
        plex_token = Settings.get(Settings.key == "api_key").value
        admin = MyPlexAccount(plex_token)
        try:
            admin.removeHomeUser(email)
        except:
            admin.removeFriend(email)
    return


def plex_invite_user(email, code):
    try:
        plex_get_users.cache_clear()
        sections = list(
            (Settings.get(Settings.key == "libraries").value).split(", "))
        plex_url = Settings.get(Settings.key == "server_url").value
        plex_token = Settings.get(Settings.key == "api_key").value
        admin = PlexServer(plex_url, plex_token)
        invitation = Invitations.select().where(Invitations.code == code).first()
        if invitation.specific_libraries != None:
            sections = list(invitation.specific_libraries.split(", "))
        try:
            allowSync = True if invitation.plex_allow_sync == 1 else False
        except:
            allowSync = False
        if Invitations.select().where(Invitations.code == code, Invitations.plex_home == 1):
            admin.myPlexAccount().createExistingUser(user=email, server=admin, sections=sections, allowSync=allowSync)
        else:
            admin.myPlexAccount().inviteFriend(user=email, server=admin, sections=sections, allowSync=allowSync)
        
        logging.info("Invited " + email + " to Plex Server")
        if Invitations.select().where(Invitations.code == code, Invitations.unlimited == 0):
            Invitations.update(used=True, used_at=datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()
        else:
            Invitations.update(used_at=datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()
    except Exception as e:
        logging.error("Failed to invite user: " + str(e))
        notify("Wizarr Error", "Wizarr Failed to Invite user: " + str(e), "skull")
    return


def plex_setup_user(token):
    try:
        plex_get_users.cache_clear()
        plex_token = Settings.get(Settings.key == "api_key").value
        admin_email = MyPlexAccount(plex_token).email
        user = MyPlexAccount(token)
        user.acceptInvite(admin_email)
        user.enableViewStateSync()
        mediarequest_import_users([user.id])
    except Exception as e:
        logging.error("Failed to setup user: " + str(e))
        
        


def plex_opt_out_online_sources(token):
    user = MyPlexAccount(token)
    for source in user.onlineMediaSources():
        source.optOut()
    return


@app.route('/scan', methods=["POST"])
def plex_scan():
    plex_url = request.args.get('plex_url')
    plex_token = request.args.get('plex_token')
    if not plex_url or not plex_token:
        abort(400)
    try:
        plex = PlexServer(plex_url, token=plex_token)
        libraries_raw = plex.library.sections()
    except:
        abort(400)
    libraries = []
    for library in libraries_raw:
        libraries.append(library.title)
    return jsonify(libraries)


@app.route('/scan-specific', methods=["POST"])
def plex_scan_specific():
    plex_url = Settings.get(Settings.key == "server_url").value
    plex_token = Settings.get(Settings.key == "api_key").value
    if not plex_url or not plex_token:
        abort(400)
    try:
        plex = PlexServer(plex_url, token=plex_token)
        libraries_raw = plex.library.sections()
    except:
        abort(400)
    libraries = []
    for library in libraries_raw:
        libraries.append(library.title)
    return jsonify(libraries)
