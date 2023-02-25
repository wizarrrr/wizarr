from plexapi.myplex import MyPlexPinLogin, MyPlexAccount, PlexServer
from app import app, Invitations, Settings, Users, scheduler
import datetime
import os
import threading
from flask import request, abort, jsonify
import logging
from cachetools import cached, TTLCache


def handleOauthToken(token, code):
    email = MyPlexAccount(token).email
    inviteUser(email, code)
    if Users.select().where(Users.email == email).exists():
        Users.delete().where(Users.email == email).execute()
    expires = datetime.datetime.now() + datetime.timedelta(days=int(Invitations.get(code=code).duration)
                                                           ) if Invitations.get(code=code).duration else None
    user = Users.create(token=token, email=email,
                        username=MyPlexAccount(token).username, code=code, expires=expires)

    user.save()
    threading.Thread(target=SetupUser, args=(token,)).start()


@cached(cache=TTLCache(maxsize=1024, ttl=600))
def getUsers():
    token = Settings.get(Settings.key == "api_key").value
    admin = MyPlexAccount(token)
    plexusers = admin.users()
    # Compare database to users

    for user in plexusers:
        if not user.email:
            user.email = "None"
        if not Users.select().where(Users.username == user.title).exists():
            Users.create(email=user.email, username=user.title,
                         token="None", code="None")
    if Users.select():
        for dbuser in Users.select():
            if dbuser.username not in [u.title for u in plexusers]:
                dbuser.delete_instance()
    return plexusers


def deleteUser(email):
    getUsers.cache_clear()
    plex_token = request.args.get('plex_token')
    admin = MyPlexAccount(plex_token)
    admin.removeFriend(email)
    Users.delete().where(Users.email == email).execute()


def inviteUser(email, code):
    getUsers.cache_clear()
    sections = list(
        (Settings.get(Settings.key == "libraries").value).split(", "))
    plex_url = Settings.get(Settings.key == "server_url").value
    plex_token = Settings.get(Settings.key == "api_key").value
    admin = PlexServer(plex_url, plex_token)
    if Invitations.select().where(Invitations.code == code, Invitations.specific_libraries != None):
        sections = list(
            (Invitations.get(Invitations.code == code).specific_libraries).split(", "))
    admin.myPlexAccount().inviteFriend(user=email, server=admin, sections=sections)
    logging.info("Invited " + email + " to Plex Server")
    if Invitations.select().where(Invitations.code == code, Invitations.unlimited == 0):
        Invitations.update(used=True, used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()
    else:
        Invitations.update(used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()
    return


def SetupUser(token):
    try:
        getUsers.cache_clear()
        plex_token = Settings.get(Settings.key == "api_key").value
        admin_email = MyPlexAccount(plex_token).email
        user = MyPlexAccount(token)
        user.acceptInvite(admin_email)
        user.enableViewStateSync()
    except Exception as e:
        logging.error("Failed to setup user: " + str(e))


def optOutOnlineSources(token):
    user = MyPlexAccount(token)
    for source in user.onlineMediaSources():
        source.optOut()
    return


@app.route('/scan', methods=["POST"])
def scan():
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
def scan_specific():
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
