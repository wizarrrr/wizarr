from plexapi.myplex import MyPlexPinLogin, MyPlexAccount, PlexServer
from app import app, Invitations, Settings, Users, Oauth
from flask import render_template, make_response, abort, request, redirect
import datetime
import os
import logging




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
            acceptInvite(user.token)
        else:
            logging.warning("User already invited: " + email)
    return


def inviteUser(email, code):
    
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

def acceptInvite(token):
    admin_email = MyPlexAccount(Settings.get(Settings.key == "plex_token").value).email
    user = MyPlexAccount(token)
    user.acceptInvite(admin_email)