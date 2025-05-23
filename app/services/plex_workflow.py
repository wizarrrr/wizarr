import datetime
import threading
import logging
from typing import List

from plexapi.myplex import MyPlexAccount
from cachetools import cached, TTLCache
from flask import copy_current_request_context
from app.extensions import db
from app.models import Invitation, User, Settings, Library
from .plex_client import PlexClient
from .notifications import notify  # your existing helper



# ─── Invite & onboarding ──────────────────────────────────────────────────
def handle_oauth_token(app, token: str, code: str) -> None:
    """Called from /join when Plex gives us a token."""
    with app.app_context():
        account = MyPlexAccount(token=token)
        email   = account.email
        
        # remove any existing DB user with that email
        db.session.query(User).filter(User.email == email).delete(synchronize_session=False)
        db.session.commit()
    
        # compute expiry if invitation has a duration
        inv = Invitation.query.filter_by(code=code).first()
        duration = inv.duration
        expires = (
            datetime.datetime.now() +
            datetime.timedelta(days=int(duration))
            if duration else None
        )
    
        # create new User row
        new_user = User(
            token=token,
            email=email,
            username=account.username,
            code=code,
            expires=expires,
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Now invite the user to Plex and associate them with the invitation
        _invite_user(email, code, new_user.id)
    
        notify(
            "User Joined",
            f"User {account.username} has joined your server!",
            "tada"
        )
    
        # background post‐join setup
        threading.Thread(
            target=_post_join_setup,
            args=(app,token),
            daemon=True
        ).start()


def _invite_user(email: str, code: str, user_id: int = None) -> None:
    client = PlexClient()
    inv = Invitation.query.filter_by(code=code).first()
    # fetch default libraries if none set on invite
    libs_setting = (
        db.session
          .query(Settings.value)
          .filter_by(key="libraries")
          .scalar()
    ) or ""
    
    
    if inv.libraries:
        libs = [lib.external_id for lib in inv.libraries]
    else:
        # fall back to your “global” set of enabled libraries:
        libs = [
            lib.external_id
            for lib in Library.query.filter_by(enabled=True).all()
        ]

    

    allow_sync = bool(inv.plex_allow_sync)

    if inv.plex_home:
        client.invite_home(email, libs, allow_sync)
    else:
        client.invite_friend(email, libs, allow_sync)

    logging.info("Invited %s to Plex", email)

    # mark invitation as used (unless unlimited) and record who/when
    if user_id:
        user = User.query.get(user_id)
        inv.used_by = user
    inv.used_at = datetime.datetime.now()
    if not inv.unlimited:
        inv.used = True
    list_users.cache_clear()
    db.session.commit()


def _post_join_setup(app, token: str):
    with app.app_context():
        client = PlexClient()
        """Run after the invite is accepted (view-state sync, opt-out etc.)."""
        try:
            user = MyPlexAccount(token=token)
            user.acceptInvite(client.admin.email)
            user.enableViewStateSync()
            _opt_out_online_sources(user)
        except Exception as exc:
            logging.error("Post-join setup failed: %s", exc)


def _opt_out_online_sources(user: MyPlexAccount):
    for src in user.onlineMediaSources():
        src.optOut()


# ─── User queries / mutate ────────────────────────────────────────────────
@cached(cache=TTLCache(maxsize=1024, ttl=600))
def list_users() -> List[User]:
    client = PlexClient()
    """
    Return Users rows with extra photo/expires fields merged in.
    Also keep DB in sync with Plex’s current user list.
    """

    server_id = client.server.machineIdentifier

    # fetch from Plex, but only users who are currently invited to this server
    plex_users = {u.email: u for u in client.admin.users() if any(s.machineIdentifier == server_id for s in u.servers)}    
    # fetch from our DB
    db_users = db.session.query(User).all()

    # delete any DB users no longer on Plex
    known_emails = set(plex_users.keys())
    for db_user in db_users:
        if db_user.email not in known_emails:
            db.session.delete(db_user)
    db.session.commit()

    # ensure every Plex user has a DB row
    for plex_user in plex_users.values():
        existing = db.session.query(User).filter_by(email=plex_user.email).first()
        if not existing:
            new_user = User(
                email=plex_user.email or "None",
                username=plex_user.title,
                token="None",
                code="None"
            )
            db.session.add(new_user)
    db.session.commit()

    # merge in photo and expires before returning
    users = db.session.query(User).all()
    for u in users:
        p = plex_users.get(u.email)
        if p:
            u.photo = p.thumb
    # no need to commit – photo is transient on the model

    return users


def delete_user(db_id: int) -> None:
    """Remove from cache, Plex, then our DB."""
    client = PlexClient()
    list_users.cache_clear()
    print("Deleting User on Plex with ID", db_id)
    email = (
        db.session
          .query(User.email)
          .filter_by(id=db_id)
          .scalar()
    )
    if email and email != "None":
        print("Deleting User on Plex")
        client.remove_user(email)

    list_users.cache_clear()
    # finally delete the record locally
    db.session.query(User).filter_by(id=db_id).delete(synchronize_session=False)
    db.session.commit()
