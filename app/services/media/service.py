"""Service layer for media server management.

This module provides a unified interface for managing users, libraries, and
operations across different media server types. It acts as a facade that
dispatches requests to the appropriate media client implementation.
"""

import logging
import re
from collections import defaultdict

from app.extensions import db
from app.models import Identity, MediaServer, Settings, User

from .client_base import CLIENTS


def _clear_user_cache(client) -> None:
    """Helper to clear user cache if available."""
    if hasattr(client, "list_users") and hasattr(client.list_users, "cache_clear"):
        client.list_users.cache_clear()


def _mode() -> str | None:
    """Read the 'server_type' setting from the database."""
    return db.session.query(Settings.value).filter_by(key="server_type").scalar()


def get_client(
    server_type: str | None = None, url: str | None = None, token: str | None = None
):
    """Instantiate the MediaClient for the given server_type, optionally overriding URL/token."""
    if server_type is None:
        server_type = _mode()

    if server_type is None:
        raise ValueError("No media server type configured")

    client_class = CLIENTS.get(server_type)
    if not client_class:
        raise ValueError(f"Unsupported media server type: {server_type}")
    client = client_class()
    if url:
        client.url = url
    if token:
        client.token = token
    return client


def get_client_for_media_server(server: MediaServer):
    """Return a configured MediaClient instance for the given MediaServer row."""
    if server.server_type not in CLIENTS:
        raise ValueError(f"Unsupported media server type: {server.server_type}")

    return CLIENTS[server.server_type](media_server=server)


def get_media_client(server_type: str, media_server: MediaServer | None = None):
    """Return a configured MediaClient instance for the given server type and optional MediaServer.

    This is an alias/wrapper around get_client_for_media_server for consistency.
    """
    if media_server:
        return get_client_for_media_server(media_server)
    return get_client(server_type)


def list_users(clear_cache: bool = False):
    """Return current users from the configured media server, syncing local DB as needed."""
    client = get_client(_mode())
    if clear_cache:
        _clear_user_cache(client)
    return client.list_users()


def list_users_for_server(server: MediaServer, *, clear_cache: bool = False):
    """List users for a specific MediaServer instance and ensure server_id set."""
    client = get_client_for_media_server(server)
    if clear_cache:
        _clear_user_cache(client)

    users = client.list_users()

    # Ensure server linkage
    changed = False
    for user in users:
        if user.server_id != server.id:
            user.server_id = server.id
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

    # server is guaranteed to be not None at this point
    assert server is not None
    # Cast to MediaServer to satisfy type checker
    from typing import cast

    server = cast(MediaServer, server)
    client = get_client_for_media_server(server)

    # clear cache pre‐removal if supported
    _clear_user_cache(client)

    try:
        if server.server_type == "plex":
            if user.email and user.email != "None":
                client.delete_user(user.email)
        else:
            client.delete_user(user.token)
    except Exception as exc:
        # log but still remove locally so UI stays consistent
        logging.error("Remote deletion failed: %s", exc)

    # Delete user from connected companion apps (Ombi, Overseerr, Audiobookrequest, etc.)
    try:
        from app.services.ombi_client import delete_user_from_connections

        connection_results = delete_user_from_connections(user.token)

        # Log companion app deletion results
        for result in connection_results:
            if result["status"] == "success":
                logging.info(
                    f"User {user.username} deleted from companion app {result.get('connection_name')}"
                )
            elif result["status"] == "error":
                logging.warning(
                    f"Failed to delete user from {result.get('connection_name')}: {result.get('message')}"
                )
    except Exception as exc:
        logging.error(f"Error deleting user from companion apps: {exc}")

    db.session.delete(user)
    db.session.commit()

    _clear_user_cache(client)


def delete_user_for_server(server: MediaServer, db_id: int) -> None:
    """Delete a user from the given MediaServer and local DB."""
    client = get_client_for_media_server(server)
    _clear_user_cache(client)

    user = db.session.get(User, db_id)
    if user:
        if server.server_type == "plex":
            email = user.email
            if email and email != "None":
                client.delete_user(email)
        else:
            client.delete_user(user.token)

        # Delete user from connected companion apps (Ombi, Overseerr, Audiobookrequest, etc.)
        try:
            from app.services.ombi_client import delete_user_from_connections

            connection_results = delete_user_from_connections(user.token)

            # Log companion app deletion results
            for result in connection_results:
                if result["status"] == "success":
                    logging.info(
                        f"User {user.username} deleted from companion app {result.get('connection_name')}"
                    )
                elif result["status"] == "error":
                    logging.warning(
                        f"Failed to delete user from {result.get('connection_name')}: {result.get('message')}"
                    )
        except Exception as exc:
            logging.error(f"Error deleting user from companion apps: {exc}")

        db.session.delete(user)
        db.session.commit()

    _clear_user_cache(client)


def scan_libraries(
    url: str | None = None, token: str | None = None, server_type: str | None = None
):
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


def get_now_playing_all_servers():
    """Get now playing status from all configured media servers.

    Returns:
        list: A list of session dictionaries from all servers, with server info included.
              Each session includes:
              - All standard now_playing fields (user_name, media_title, etc.)
              - server_name: Name of the media server
              - server_type: Type of media server (plex, jellyfin, etc.)
              - server_id: ID of the MediaServer record
    """
    all_sessions = []

    # Get all configured media servers
    servers = db.session.query(MediaServer).all()

    for server in servers:
        try:
            client = get_client_for_media_server(server)
            sessions = client.now_playing()

            # Add server information to each session
            for session in sessions:
                session["server_name"] = server.name
                session["server_type"] = server.server_type
                session["server_id"] = server.id
                all_sessions.append(session)

        except Exception as exc:
            logging.warning(
                f"Failed to get now playing from server {server.name} ({server.server_type}): {exc}"
            )
            continue

    return all_sessions


def get_now_playing_for_server(server_id: int):
    """Get now playing status from a specific media server.

    Args:
        server_id: ID of the MediaServer to query

    Returns:
        list: A list of session dictionaries from the specified server.
    """
    server = db.session.query(MediaServer).filter_by(id=server_id).first()
    if not server:
        return []

    try:
        client = get_client_for_media_server(server)
        sessions = client.now_playing()

        # Add server information to each session
        for session in sessions:
            session["server_name"] = server.name
            session["server_type"] = server.server_type
            session["server_id"] = server.id

        return sessions

    except Exception as exc:
        logging.warning(
            f"Failed to get now playing from server {server.name} ({server.server_type}): {exc}"
        )
        return []


EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _auto_link_identities():
    """Group accounts that share the *same, valid* email address.

    Users imported from Plex/Jellyfin which lack a real email often use
    placeholders like "None" or "empty".  Linking those together would create
    one giant pseudo-identity, so we now skip addresses that don't match a
    simple *user@host* pattern.
    """

    users = db.session.query(User).filter(User.email.isnot(None)).all()

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
