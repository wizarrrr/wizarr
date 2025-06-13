"""Facade that dispatches media user management to Plex or Jellyfin."""

from app.extensions import db
from app.models import Settings, User, MediaServer, Identity
from .client_base import CLIENTS
from collections import defaultdict
import re


def _mode() -> str:
    """
    Reads the 'server_type' setting from the DB.
    Falls back to None if it isn't set.
    """
    return (
        db.session
          .query(Settings.value)
          .filter_by(key="server_type")
          .scalar()
    )


def get_client(server_type: str | None = None, url: str | None = None, token: str | None = None):
    """
    Instantiate the MediaClient for the given server_type, optionally overriding URL/token.
    """
    if server_type is None:
        server_type = _mode()
    try:
        cls = CLIENTS[server_type]
    except KeyError:
        raise ValueError(f"Unsupported media server type: {server_type}")
    client = cls()
    if url:
        client.url = url
    if token:
        client.token = token
    return client


def get_client_for_media_server(server: MediaServer):
    """Return a configured MediaClient instance for the given MediaServer row."""
    cls = CLIENTS.get(server.server_type)
    if not cls:
        raise ValueError(f"Unsupported media server type: {server.server_type}")

    # MediaClient can now accept the row directly which centralises
    # credential handling and attribute population.
    client = cls(media_server=server)
    return client


def list_users(clear_cache: bool = False):
    """
    Return current users from the configured media server, syncing local DB as needed.
    """
    client = get_client(_mode())
    # clear cache on clients that support it
    if clear_cache and hasattr(client, 'list_users') and hasattr(client.list_users, 'cache_clear'):
        client.list_users.cache_clear()
    return client.list_users()


def list_users_for_server(server: MediaServer, *, clear_cache: bool = False):
    """List users for a specific MediaServer instance and ensure server_id set."""
    client = get_client_for_media_server(server)
    if clear_cache and hasattr(client, 'list_users') and hasattr(client.list_users, 'cache_clear'):
        client.list_users.cache_clear()
    users = client.list_users()
    # ensure linkage
    changed = False
    for u in users:
        if u.server_id != server.id:
            u.server_id = server.id
            changed = True
    if changed:
        db.session.commit()
    return users


def delete_user(db_id: int) -> None:
    """Delete a user from its associated MediaServer and local DB."""
    user = db.session.get(User, db_id)
    if not user:
        return

    server = user.server
    if server is None:
        # fallback: derive from token? Skip remote deletion
        db.session.delete(user)
        db.session.commit()
        return

    client = get_client_for_media_server(server)

    # clear cache pre‐removal if supported
    if hasattr(client, 'list_users') and hasattr(client.list_users, 'cache_clear'):
        client.list_users.cache_clear()

    try:
        if server.server_type == 'plex':
            if user.email and user.email != 'None':
                client.delete_user(user.email)
        else:
            client.delete_user(user.token)
    except Exception as exc:
        # log but still remove locally so UI stays consistent
        import logging
        logging.error("Remote deletion failed: %s", exc)

    db.session.delete(user)
    db.session.commit()

    if hasattr(client, 'list_users') and hasattr(client.list_users, 'cache_clear'):
        client.list_users.cache_clear()


def delete_user_for_server(server: MediaServer, db_id: int) -> None:
    """Delete a user from the given MediaServer and local DB."""
    client = get_client_for_media_server(server)
    if hasattr(client, 'list_users') and hasattr(client.list_users, 'cache_clear'):
        client.list_users.cache_clear()

    user = db.session.get(User, db_id)
    if user:
        if server.server_type == 'plex':
            email = user.email
            if email and email != 'None':
                client.delete_user(email)
        else:
            client.delete_user(user.token)
        db.session.delete(user)
        db.session.commit()

    if hasattr(client, 'list_users') and hasattr(client.list_users, 'cache_clear'):
        client.list_users.cache_clear()


def scan_libraries(url: str | None = None, token: str | None = None, server_type: str | None = None):
    """
    Fetch available libraries from the media server, given optional credentials or using Settings.
    Returns a mapping of external_id -> display_name.
    """
    client = get_client(server_type, url, token)
    return client.libraries()


def scan_libraries_for_server(server: MediaServer):
    """Scan libraries for the given server and upsert into our Library table."""
    client = get_client_for_media_server(server)
    return client.libraries()


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _auto_link_identities():
    """Group accounts that share the *same, valid* email address.

    Users imported from Plex/Jellyfin which lack a real email often use
    placeholders like "None" or "empty".  Linking those together would create
    one giant pseudo-identity, so we now skip addresses that don't match a
    simple *user@host* pattern.
    """

    users = (
        db.session.query(User)
        .filter(User.email.isnot(None))
        .all()
    )

    buckets: dict[str, list[User]] = defaultdict(list)
    for u in users:
        email = (u.email or "").strip()
        if not EMAIL_RE.fullmatch(email):
            # ignore invalid / placeholder addresses
            continue
        buckets[email.lower()].append(u)

    for same in buckets.values():
        if len(same) < 2:
            continue  # nothing to link

        identity = same[0].identity or Identity(
            primary_email=same[0].email,
            primary_username=same[0].username,
        )
        db.session.add(identity)
        db.session.flush()

        for u in same:
            u.identity_id = identity.id

    db.session.commit()


def list_users_all_servers(clear_cache: bool = False):
    """Return users for all servers (mapping server -> list)."""
    _auto_link_identities()
    res = {}
    for server in db.session.query(MediaServer).all():
        try:
            res[server.id] = list_users_for_server(server, clear_cache=clear_cache)
        except Exception:
            res[server.id] = []
    return res