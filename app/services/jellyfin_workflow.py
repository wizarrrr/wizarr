import datetime
import logging
import re
from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, User, Settings
from .jellyfin_client import JellyfinClient
from .notifications import notify
from .invites import is_invite_valid  # helper moved to services/helpers.py



# ─── Public sign-up flow ─────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")

def join(username: str, password: str, confirm: str, email: str, code: str) -> tuple[bool, str]:
    client = JellyfinClient()
    """Return (success, error-msg) – called from the /wizard front end."""
    # validate inputs
    if not EMAIL_RE.fullmatch(email):
        return False, "Invalid e-mail address."
    if not 8 <= len(password) <= 20:
        return False, "Password must be 8-20 characters."
    if password != confirm:
        return False, "Passwords do not match."

    # validate invite code
    ok, msg = is_invite_valid(code)
    if not ok:
        return False, msg

    # check user/email uniqueness
    existing = User.query.filter(or_(User.username == username,
                                     User.email == email)).first()
    if existing:
        return False, "User or e-mail already exists."

    try:
        # create on Jellyfin side
        user_id = client.create_user(username, password)

        # load invite and settings
        inv = Invitation.query.filter_by(code=code).first()
        libs_setting = (
            db.session.query(Settings.value)
                      .filter_by(key="libraries")
                      .scalar()
        ) or ""
        sections = (inv.specific_libraries or libs_setting).split(", ")
        set_specific_folders(client, user_id, sections)

        # compute expiry
        expires = None
        if inv.duration:
            expires = datetime.datetime.now() + datetime.timedelta(days=int(inv.duration))

        # create DB user
        new_user = User(
            username=username,
            email=email,
            password=password,
            token=user_id,
            code=code,
            expires=expires
        )
        db.session.add(new_user)
        db.session.commit()

        # mark invite used and notify
        _mark_invite_used(inv, email)
        notify("New User", f"User {username} has joined your server!", "tada")
        return True, ""

    except Exception as exc:
        db.session.rollback()
        logging.error("Jellyfin join error: %s", exc, exc_info=True)
        return False, "An unexpected error occurred."


def _mark_invite_used(inv: Invitation, email: str) -> None:
    """Mark the invitation as used in the database."""
    inv.used = True if not inv.unlimited else inv.used
    inv.used_at = datetime.datetime.now()
    inv.used_by = email
    db.session.commit()

def _folder_name_to_id(name: str, cache: dict[str, str]) -> str | None:
    """Convert 'Movies' → '6c8ee2dc…'.  Build cache once per request."""
    return cache.get(name)

def set_specific_folders(client: JellyfinClient, user_id: str, names: list[str]):
    # build a {Name: Id} cache
    mapping = {item["Name"]: item["Id"]
               for item in client.get("/Library/MediaFolders").json()["Items"]}

    folder_ids = [_folder_name_to_id(n, mapping) for n in names]
    folder_ids = [fid for fid in folder_ids if fid]        # drop unknown names

    policy_patch = {
        "EnableAllFolders": not folder_ids,   # tick if list empty
        "EnabledFolders":    folder_ids,
    }

    current = client.get(f"/Users/{user_id}").json()["Policy"]
    current.update(policy_patch)
    client.set_policy(user_id, current)

# ─── Admin-side helpers – mirror the Plex API we already exposed ──────────
def list_users() -> list[User]:
    client = JellyfinClient()
    """Synchronise users from Jellyfin and return current list."""
    jf_users = {u["Id"]: u for u in client.get("/Users").json()}

    # upsert users
    for jf in jf_users.values():
        existing = User.query.filter_by(token=jf["Id"]).first()
        if not existing:
            new = User(
                token=jf["Id"],
                username=jf["Name"],
                email="empty",
                code="empty",
                password="empty"
            )
            db.session.add(new)
    db.session.commit()

    # remove local users no longer in Jellyfin
    for dbu in User.query.all():
        if dbu.token not in jf_users:
            db.session.delete(dbu)
    db.session.commit()

    return User.query.all()


def delete_user(db_id: int) -> None:
    """Delete a user on Jellyfin and in the local database."""
    client = JellyfinClient()
    try:
        user = db.session.get(User, db_id)
        if user:
            client.delete_user(user.token)
    except Exception as exc:
        logging.error("Delete Jellyfin user failed: %s", exc)
    finally:
        if user:
            db.session.delete(user)
            db.session.commit()
