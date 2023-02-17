from plexapi.myplex import MyPlexPinLogin, MyPlexAccount, PlexServer
from app import app, Invitations, Settings, Users, Oauth, ExpiringInvitations, scheduler
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

    if Invitations.select().where(Invitations.code == code, Invitations.duration != None):

        # Set Expires, duration is in days, in format %Y-%m-%d %H:%M
        expires = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M") + datetime.timedelta(
            days=int(Invitations.get(Invitations.code == code).duration))

        ExpiringInvitations.create(code=code, created=datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"), used_by=Users.get(Users.email == email).id, expires=expires)


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


@scheduler.task('interval', id='checkExpiring', minutes=15, misfire_grace_time=900)
def checkExpiring():
    expiring = ExpiringInvitations.select().where(ExpiringInvitations.expires <
                                                  datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    for invite in expiring:
        deleteUser(Users.get_by_id(invite.used_by).email)
        ExpiringInvitations.delete().where(
            ExpiringInvitations.used_by == invite.used_by).execute()
