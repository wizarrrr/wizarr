"""Service layer for media server management.

This module provides a unified interface for managing users, libraries, and
operations across different media server types. It acts as a facade that
dispatches requests to the appropriate media client implementation.
"""

import copy
import logging
import re
from collections import defaultdict
from time import monotonic
from typing import Any

from app.extensions import db
from app.models import Identity, MediaServer, Settings, User

from .client_base import CLIENTS

_NOW_PLAYING_CACHE_TTL = 5.0  # seconds
_now_playing_cache: dict[str, Any] = {"timestamp": 0.0, "sessions": []}


def _get_user_identifier(user: User, server: MediaServer) -> str:
    """Get user identifier for API calls (email for Plex, token for others)."""
    if server.server_type == "plex":
        if user.email and user.email != "None":
            return user.email
        raise ValueError(f"Plex user {user.id} has no valid email")
    return user.token


def _delete_from_companion_apps(user: User) -> None:
    """Delete user from connected companion apps (Ombi, Overseerr, etc.)."""
    try:
        from app.services.ombi_client import delete_user_from_connections

        connection_results = delete_user_from_connections(user.token)

        for result in connection_results:
            if result["status"] == "success":
                logging.info(
                    f"User {user.username} deleted from {result.get('connection_name')}"
                )
            elif result["status"] == "error":
                logging.warning(
                    f"Failed to delete from {result.get('connection_name')}: {result.get('message')}"  # noqa: S608  # Logging f-string, not SQL query
                )
    except Exception as exc:
        logging.error(f"Error deleting from companion apps: {exc}")


def _set_user_enabled_state(db_id: int, enabled: bool) -> bool:
    """Enable or disable a user on their media server."""
    if not (user := db.session.get(User, db_id)):
        logging.error(f"User with id {db_id} not found")
        return False

    if not user.server:
        logging.warning(f"User {db_id} has no associated server")
        return False

    try:
        client = get_client_for_media_server(user.server)
        user_identifier = _get_user_identifier(user, user.server)
        method = client.enable_user if enabled else client.disable_user
        result = method(user_identifier)

        action = "enabled" if enabled else "disabled"
        if result:
            logging.info(
                f"Successfully {action} user {user.username} (ID: {db_id}) on {user.server.server_type}"
            )
        else:
            logging.warning(
                f"Failed to {action} user {user.username} (ID: {db_id}) on {user.server.server_type}"
            )

        return result
    except Exception as exc:
        logging.error(
            f"Error {'enabling' if enabled else 'disabling'} user {db_id}: {exc}"
        )
        return False


def _mode() -> str | None:
    """Read the 'server_type' setting from the database."""
    return (
        db.session.query(Settings.value).filter_by(key="server_type").scalar()
    )  # SQLAlchemy filter_by uses parameterized queries


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


def list_users():
    """Return current users from the configured media server, syncing local DB as needed."""
    return get_client(_mode()).list_users()


def list_users_for_server(server: MediaServer):
    """List users for a specific MediaServer instance."""
    return get_client_for_media_server(server).list_users()


def delete_user(db_id: int) -> None:
    """Delete a user from its associated MediaServer and local DB."""
    if not (user := db.session.get(User, db_id)):
        return

    if not user.server:
        db.session.delete(user)
        db.session.commit()
        return

    # Delete from remote media server
    try:
        client = get_client_for_media_server(user.server)
        user_identifier = _get_user_identifier(user, user.server)
        client.delete_user(user_identifier)
    except Exception as exc:
        logging.error("Remote deletion failed: %s", exc)

    # Delete from companion apps
    _delete_from_companion_apps(user)

    db.session.delete(user)
    db.session.commit()


def enable_user(db_id: int) -> bool:
    """Enable a user on its associated MediaServer."""
    return _set_user_enabled_state(db_id, enabled=True)


def disable_user(db_id: int) -> bool:
    """Disable a user on its associated MediaServer."""
    return _set_user_enabled_state(db_id, enabled=False)


def remove_user_from_server(user_id: int, server_id: int) -> bool:
    """Remove a user from a specific server only, preserving other server accounts.

    Args:
        user_id: The ID of the user record to remove
        server_id: The ID of the server to remove the user from

    Returns:
        bool: True if removal was successful, False if user/server not found
    """
    user = db.session.get(User, user_id)
    server = db.session.get(MediaServer, server_id)

    if not user or not server or user.server_id != server_id:
        return False

    # Remove from remote media server
    try:
        client = get_client_for_media_server(server)
        user_identifier = _get_user_identifier(user, server)
        client.delete_user(user_identifier)
    except Exception as exc:
        logging.error(
            f"Remote deletion failed for user {user.username} from {server.name}: {exc}"
        )

    # Check if user has other accounts
    has_other_accounts = (
        user.identity_id
        and User.query.filter(
            User.identity_id == user.identity_id,
            User.server_id != server_id,
            User.id != user_id,
        ).count()
        > 0
    )

    # Delete from companion apps only if this is the user's only account
    if not has_other_accounts:
        _delete_from_companion_apps(user)

    db.session.delete(user)
    db.session.commit()

    if has_other_accounts:
        logging.info(
            f"Removed user {user.username} from server {server.name}, preserving other accounts"
        )
    else:
        logging.info(
            f"Removed user {user.username}'s only account from server {server.name}"
        )

    return True


def scan_libraries(
    url: str | None = None, token: str | None = None, server_type: str | None = None
):
    """Fetch available libraries from the media server using optional credentials.

    This is used for scanning libraries before a server is saved to the database.
    For saved servers, use scan_libraries_for_server() instead.
    """
    client = get_client(server_type, url, token)
    return client.libraries()


def scan_libraries_for_server(server: MediaServer):
    """Scan libraries for the given server and upsert into our Library table."""
    client = get_client_for_media_server(server)
    return client.libraries()


def get_now_playing_all_servers(
    *, use_cache: bool = True, cache_ttl: float = _NOW_PLAYING_CACHE_TTL
):
    """Get now playing status from all configured media servers.

    Returns:
        list: A list of session dictionaries from all servers, with server info included.
              Each session includes:
              - All standard now_playing fields (user_name, media_title, etc.)
              - server_name: Name of the media server
              - server_type: Type of media server (plex, jellyfin, etc.)
              - server_id: ID of the MediaServer record
    """
    if use_cache:
        now = monotonic()
        cached_ts = _now_playing_cache.get("timestamp", 0.0)
        if now - cached_ts <= cache_ttl:
            return copy.deepcopy(_now_playing_cache.get("sessions", []))

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

    if use_cache:
        _now_playing_cache["timestamp"] = monotonic()
        _now_playing_cache["sessions"] = all_sessions
        return copy.deepcopy(all_sessions)

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


def list_users_all_servers():
    """Return users for all servers (mapping server -> list)."""
    _auto_link_identities()
    res = {}
    for server in db.session.query(MediaServer).all():
        try:
            res[server.id] = list_users_for_server(server)
        except Exception:
            res[server.id] = []
    return res
