from plexapi.myplex import MyPlexPinLogin, MyPlexAccount, PlexServer
from app import app, Invitations, Settings, Users, Oauth
import datetime
import os
import threading
from flask import request, abort, jsonify
import logging
from cachetools import cached, TTLCache


def plexoauth(id, code):
    oauth = MyPlexPinLogin(oauth=True)
    url = oauth.oauthUrl(forwardUrl=(os.getenv('APP_URL') + '/setup'))

    Oauth.update(url=url).where(Oauth.id == id).execute()

    oauth.run(timeout=120)
    oauth.waitForLogin()
    token = oauth.token
    if not token:
        logging.error("Failed to get token from Plex")
    if token:
        email = MyPlexAccount(token).email
        if not Users.select().where(Users.email == email).exists():
            user = Users.create(token=token, email=email,
                                username=MyPlexAccount(token).username, code=code)
            user.save()
            inviteUser(user.email, code)
            threading.Thread(target=SetupUser, args=(token,)).start()

        else:
            logging.warning("User already invited: " + email)
    return

@cached(cache=TTLCache(maxsize=1024, ttl=600))
def getUsers():
    admin = MyPlexAccount(Settings.get(Settings.key == "plex_token").value)
    users = admin.users()
    return users


def deleteUser(email):
    getUsers.cache_clear()
    admin = MyPlexAccount(Settings.get(Settings.key == "plex_token").value)
    admin.removeFriend(email)
    Users.delete().where(Users.email == email).execute()


def inviteUser(email, code):
    getUsers.cache_clear()
    sections = list(
        (Settings.get(Settings.key == "plex_libraries").value).split(", "))
    admin = PlexServer(Settings.get(Settings.key == "plex_url").value, Settings.get(
        Settings.key == "plex_token").value)
    admin.myPlexAccount().inviteFriend(user=email, server=admin, sections=sections)
    logging.info("Invited " + email + " to Plex Server")
    if Invitations.select().where(Invitations.code == code, Invitations.unlimited == 0):
        Invitations.update(used=True, used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()
    else:
        Invitations.update(used_at=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=email).where(Invitations.code == code).execute()

def SetupUser(token):
    try:
        getUsers.cache_clear()
        admin_email = MyPlexAccount(Settings.get(
            Settings.key == "plex_token").value).email
        user = MyPlexAccount(token)
        user.acceptInvite(admin_email)
        user.enableViewStateSync()
    except Exception as e:
        logging.error("Failed to setup user: " + str(e))


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