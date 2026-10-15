"""Service layer for media server management.

This module provides a unified interface for managing users, libraries, and
operations across different media server types. It acts as a facade that
dispatches requests to the appropriate media client implementation.
"""

import copy
import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import wait as wait_for_futures
from time import monotonic
from typing import Any

from flask import current_app

from app.extensions import db
from app.models import Identity, MediaServer, Settings, User

from .client_base import CLIENTS, EMAIL_RE

# ---------------------------------------------------------------------------
# Now playing
# ---------------------------------------------------------------------------

# The dashboard polls now playing every 10 s. The TTL is a little longer than
# that, so that a poll can use the result of the previous one, and other tabs
# and the health card share the same fetch.
_NOW_PLAYING_CACHE_TTL = 12.0  # seconds
# Short (connect, read) timeouts, so that one slow server does not hold the poll.
NOW_PLAYING_TIMEOUT: tuple[float, float] = (3, 10)
# Maximum wall time for one fetch from all servers.
NOW_PLAYING_DEADLINE = 15.0  # seconds

_now_playing_cache: dict[str, Any] = {"timestamp": float("-inf"), "sessions": []}
# Held while one caller fetches, so that concurrent callers share that fetch.
_now_playing_fetch_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Server health
# ---------------------------------------------------------------------------

HEALTH_TIMEOUT: tuple[float, float] = (3, 10)
HEALTH_DEADLINE = 15.0  # seconds
# Results stay valid for this time. Failures stay too, so an offline server
# fails fast on the next request.
HEALTH_CACHE_TTL = 30.0  # seconds

_health_cache: dict[int, dict[str, Any]] = {}
_health_cache_lock = threading.Lock()
# Held while one caller fetches, so that concurrent callers share that fetch.
_health_fetch_lock = threading.Lock()

# ---------------------------------------------------------------------------
# User sync throttle
# ---------------------------------------------------------------------------

# A full remote user sync runs at most one time in this period for each server,
# unless the caller forces it.
USER_SYNC_MAX_AGE = 300.0  # seconds

# server_id -> (monotonic time of the last successful sync, server fingerprint)
_user_sync_done: dict[int, tuple[float, tuple]] = {}
_user_sync_state_lock = threading.Lock()
# One lock for each server, so that two callers do not sync the same server
# at the same time.
_user_sync_server_locks: dict[int, threading.Lock] = {}

# ---------------------------------------------------------------------------
# Parallel calls to media servers
# ---------------------------------------------------------------------------

# Most installs have few servers. This limit keeps the number of threads and
# of DB connections that the workers use small.
_MAX_PARALLEL_SERVERS = 8


def run_parallel(
    jobs: list[Callable[[], Any]], *, deadline: float
) -> list[tuple[str, Any]]:
    """Run each job in a worker thread and wait ``deadline`` seconds at most.

    Each worker pushes a new Flask app context, so a job that reads the DB
    gets its own session. Make the media clients in the calling thread, from
    rows of the calling thread's session. Do not write to the DB in a job.

    Returns one ``(status, value)`` pair for each job, in the order of
    ``jobs``: ``("ok", result)``, ``("error", exception)`` or
    ``("timeout", None)``. A job that still runs at the deadline continues in
    the background, but nothing uses its result.
    """
    if not jobs:
        return []

    app = current_app._get_current_object()  # type: ignore[attr-defined]

    def _call(job: Callable[[], Any]) -> Any:
        with app.app_context():
            return job()

    executor = ThreadPoolExecutor(
        max_workers=min(len(jobs), _MAX_PARALLEL_SERVERS),
        thread_name_prefix="wizarr-media",
    )
    futures = []
    try:
        futures = [executor.submit(_call, job) for job in jobs]
        wait_for_futures(futures, timeout=deadline)
    finally:
        # Do not wait for a server that does not answer. Jobs that did not
        # start yet are cancelled.
        executor.shutdown(wait=False, cancel_futures=True)

    results: list[tuple[str, Any]] = []
    for future in futures:
        if future.cancelled() or not future.done():
            results.append(("timeout", None))
        elif (exc := future.exception()) is not None:
            results.append(("error", exc))
        else:
            results.append(("ok", future.result()))
    return results


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


def _set_user_enabled_state(db_id: int, enabled: bool, *, commit: bool = True) -> bool:
    """Enable or disable a user and save the local state.

    Set ``commit`` to ``False`` when the caller owns the transaction.
    """
    if not (user := db.session.get(User, db_id)):
        logging.error(f"User with id {db_id} not found")
        return False

    if not user.server:
        logging.warning(f"User {db_id} has no associated server")
        return False

    try:
        client = get_client_for_media_server(user.server)  # type: ignore
        user_identifier = _get_user_identifier(user, user.server)  # type: ignore
        method = client.enable_user if enabled else client.disable_user
        result = method(user_identifier)

        action = "enabled" if enabled else "disabled"
        if result:
            user.is_disabled = not enabled
            if commit:
                db.session.commit()
            else:
                db.session.flush()
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


# Order of the server-type picker, kept as it has always appeared. Anything else
# registered is appended alphabetically, so a new client shows up in the create and
# edit modals without anyone editing a template.
_SERVER_TYPE_ORDER = (
    "plex",
    "jellyfin",
    "emby",
    "audiobookshelf",
    "romm",
    "komga",
    "kavita",
)


def server_type_choices(current: str | None = None) -> list[tuple[str, str]]:
    """Return ``(server_type, label)`` pairs for every registered media client.

    ``current`` is the type of a server being edited. It is always included, even
    when no client is registered for it, so saving the edit form can never
    silently rewrite the stored type to whichever option happens to come first.
    """
    names = [n for n in _SERVER_TYPE_ORDER if n in CLIENTS]
    names += sorted(n for n in CLIENTS if n not in _SERVER_TYPE_ORDER)
    if current and current not in names:
        names.insert(0, current)
    return [(name, name.title()) for name in names]


def check_server_connection(server_type: str, url: str, token: str) -> tuple[bool, str]:
    """Run the registered client's connection check for ``server_type``.

    An unknown type is refused with a message naming it, rather than being
    checked as if it were some other server type.
    """
    client_class = CLIENTS.get(server_type)
    if client_class is None:
        return False, f"Unknown server type '{server_type}'"
    return client_class.check_connection(url, token)


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
    """List users for a specific MediaServer instance.

    This always runs the remote sync. Use ``sync_users`` for a throttled sync.
    """
    # Read these before the sync. The sync commits, and that expires the row.
    server_id = server.id
    fingerprint = _user_sync_fingerprint(server)
    client = get_client_for_media_server(server)
    users = client.list_users()
    if getattr(client, "remote_errors", 0):
        # The client caught a remote error and returned the stored users.
        # Do not record a sync, so that the next call tries again.
        logging.info(
            "User sync of server %s had remote errors. It is not recorded.",
            server_id,
        )
    else:
        _record_user_sync(server_id, fingerprint)
    return users


def delete_user(
    db_id: int, *, commit: bool = True, require_remote: bool = False
) -> None:
    """Delete a user from its associated MediaServer and local DB.

    Set ``commit`` to ``False`` when the caller owns the transaction.

    With ``require_remote`` a failed delete on the media server raises and
    nothing is deleted, so the caller can retry later. A user the server no
    longer has (404) counts as deleted. Without it, a remote failure is
    logged and the local row is deleted anyway.

    Foreign key relationships are handled automatically by SQLite CASCADE/SET NULL:
    - activity_session.wizarr_user_id: CASCADE (auto-deleted)
    - invitation_user.user_id: CASCADE (auto-deleted)
    - invitation.used_by_id: SET NULL (auto-cleared)
    """
    if not (user := db.session.get(User, db_id)):
        return

    # Delete from the media server first, so a required delete that fails
    # leaves everything else in place.
    if user.server:
        try:
            client = get_client_for_media_server(user.server)  # type: ignore
            user_identifier = _get_user_identifier(user, user.server)  # type: ignore
            client.delete_user(user_identifier)
        except Exception as exc:
            if require_remote and not _is_not_found(exc):
                raise
            logging.error("Remote deletion failed: %s", exc)

    # Delete from LDAP if user is an LDAP user
    # Only delete from LDAP if this is the last User record with the same username
    if user.is_ldap_user:
        try:
            from app.models import LDAPConfiguration

            # Check if there are other User records with the same username
            other_users_count = User.query.filter(
                User.username == user.username, User.is_ldap_user, User.id != user.id
            ).count()

            # Only delete from LDAP if this is the last user with this username
            if other_users_count == 0:
                ldap_config = LDAPConfiguration.query.filter_by(enabled=True).first()
                if ldap_config:
                    from app.services.ldap.client import LDAPClient

                    ldap_client = LDAPClient(ldap_config)
                    user_dn = ldap_client.find_user_dn(user.username)
                    if not user_dn:
                        logging.warning(
                            "LDAP user DN not found for %s, skipping deletion",
                            user.username,
                        )
                    else:
                        success, message = ldap_client.delete_user(user_dn)
                        if not success:
                            logging.error(
                                "LDAP deletion failed for %s: %s", user_dn, message
                            )
                        else:
                            logging.info("Deleted LDAP user: %s", user_dn)
        except Exception as exc:
            logging.error("LDAP deletion error: %s", exc)

    # Delete from companion apps
    _delete_from_companion_apps(user)

    # Delete the user - SQLite handles all foreign key cascades automatically
    db.session.delete(user)
    if commit:
        db.session.commit()
    else:
        db.session.flush()


def _is_not_found(exc: Exception) -> bool:
    """True when a media server answered 404, i.e. the user is already gone."""
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) == 404


def enable_user(db_id: int, *, commit: bool = True) -> bool:
    """Enable a user on its associated MediaServer."""
    return _set_user_enabled_state(db_id, enabled=True, commit=commit)


def disable_user(db_id: int, *, commit: bool = True) -> bool:
    """Disable a user on its associated MediaServer."""
    return _set_user_enabled_state(db_id, enabled=False, commit=commit)


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


def scan_libraries_for_server(server: MediaServer) -> tuple[Any, bool]:
    """Scan libraries for the given server and upsert into our Library table.

    Returns ``(scan_result, authoritative)``. ``authoritative`` reports whether
    ``scan_result`` can be trusted to reconcile libraries that are missing from
    it as actually removed - see ``MediaClient.libraries_scan_authoritative``
    and ``upsert_scanned_libraries``. Callers that only add/update and never
    reconcile removals (e.g. the API library listing) can ignore it.
    """
    client = get_client_for_media_server(server)
    scan_result = client.libraries()
    return scan_result, client.libraries_scan_authoritative(scan_result)


def upsert_scanned_libraries(
    server: MediaServer, scan_result: Any, *, authoritative: bool = True
) -> None:
    """Reconcile a server's Library rows with a scan result. Does not commit.

    ``scan_result`` is either a ``{external_id: name}`` dict or a list of names.
    Existing rows keep their primary key (so invites keep referencing them) and
    their ``enabled`` flag, which is the admin's saved default and what the
    checkbox partial renders from. New libraries are inserted enabled. A library
    that vanished from the scan is disabled if any invitation still references it,
    otherwise deleted, but only when ``authoritative`` is true.

    ``authoritative`` (see ``scan_libraries_for_server``) is the caller's signal
    that ``scan_result`` genuinely reflects the server's current libraries, not
    a guess based on counts alone: a same-size scan can still have silently
    swapped in a different library, and a real removal must not be blocked
    forever just because it shrinks the count. When it's false, removal
    reconciliation is skipped entirely; adds and name updates still apply, so
    genuinely new libraries always show up.

    A malformed ``scan_result`` (e.g. ``None``) is treated the same as an empty
    one rather than raising, so a bad result from one server in a multi-server
    scan can't abort reconciliation already done for earlier servers in the
    same request.

    Shared by the invite modal scan and the server edit-form scan; each caller
    keeps its own handling of a failed scan and its own commit/flush.
    """
    from app.models import Library, invite_libraries

    try:
        pairs = list(
            scan_result.items()
            if isinstance(scan_result, dict)
            else [(name, name) for name in scan_result]
        )
    except TypeError:
        pairs = []

    # A scan that returns nothing must not mutate anything: Plex's global-id source
    # can transiently return an empty librarySections list, and trusting it would
    # disable or delete every real library and wipe the admin's invite defaults.
    if not pairs:
        return

    existing_libs = {
        lib.external_id: lib
        for lib in Library.query.filter_by(server_id=server.id).all()
    }

    incoming_ids: set[str] = set()
    for fid, name in pairs:
        fid = str(fid)
        incoming_ids.add(fid)
        if fid in existing_libs:
            existing_libs[fid].name = name
        else:
            db.session.add(
                Library(
                    external_id=fid,
                    name=name,
                    server_id=server.id,
                    enabled=True,
                )
            )

    if not authoritative:
        return

    for ext, lib in existing_libs.items():
        if str(ext) not in incoming_ids:
            referenced = db.session.execute(
                invite_libraries.select().where(invite_libraries.c.library_id == lib.id)
            ).first()
            if referenced:
                lib.enabled = False
            else:
                db.session.delete(lib)


def reset_user_password(db_id: int, new_password: str) -> bool:
    """Reset the password for a user on LDAP and/or their associated media server.

    Args:
        db_id: ID of the User row in our database
        new_password: The new password to set (already validated for length by caller)

    Returns:
        bool: True if the password was successfully reset on LDAP or media server, False otherwise
    """
    user = db.session.get(User, db_id)
    if not user:
        logging.error(f"User with id {db_id} not found")
        return False

    # Basic safeguard – keep consistent with join rules
    if not (8 <= len(new_password) <= 128):
        logging.warning("Password does not meet length requirements")
        return False

    ldap_success = False
    media_server_success = False

    # Reset LDAP password if user is an LDAP user
    # Only reset LDAP password once even if multiple User records share the same username
    if user.is_ldap_user:
        try:
            from app.models import LDAPConfiguration

            ldap_config = LDAPConfiguration.query.filter_by(enabled=True).first()
            if ldap_config:
                from app.services.ldap.client import LDAPClient

                ldap_client = LDAPClient(ldap_config)
                user_dn = ldap_client.find_user_dn(user.username)
                if not user_dn:
                    logging.error(
                        "LDAP user DN not found for %s, cannot reset password",
                        user.username,
                    )
                else:
                    success, message = ldap_client.change_password(
                        user_dn, new_password
                    )
                    if success:
                        logging.info(
                            "Successfully reset LDAP password for %s (user %s, id=%s)",
                            user_dn,
                            user.username,
                            db_id,
                        )
                        ldap_success = True
                    else:
                        logging.error(
                            "Failed to reset LDAP password for %s: %s",
                            user_dn,
                            message,
                        )
        except Exception as exc:
            logging.error(f"LDAP password reset error: {exc}")

    # Reset media server password if user has an associated server
    if user.server:
        try:
            client = get_client_for_media_server(user.server)
            user_identifier = _get_user_identifier(user, user.server)
            result = client.reset_password(user_identifier, new_password)

            if result:
                logging.info(
                    f"Successfully reset password for user {user.username} (id={db_id}) on {user.server.name}"
                )
                media_server_success = True
            else:
                logging.warning(
                    f"Failed to reset password for user {user.username} (id={db_id}) on {user.server.name}"
                )
        except Exception as exc:
            logging.error(f"Media server password reset error: {exc}")

    # Return True if either LDAP or media server password reset succeeded
    return ldap_success or media_server_success


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
    if not use_cache:
        return _fetch_now_playing_all_servers()

    cached = _cached_now_playing(cache_ttl)
    if cached is not None:
        return cached

    with _now_playing_fetch_lock:
        # Another caller can have filled the cache while this one waited.
        cached = _cached_now_playing(cache_ttl)
        if cached is not None:
            return cached

        all_sessions = _fetch_now_playing_all_servers()
        _now_playing_cache["sessions"] = all_sessions
        _now_playing_cache["timestamp"] = monotonic()
        return copy.deepcopy(all_sessions)


def _cached_now_playing(cache_ttl: float) -> list[dict] | None:
    """Return a copy of the cached sessions, or None when the cache is old.

    Read the timestamp first. The writer sets the sessions first, so a fresh
    timestamp always comes with the sessions of that fetch or a newer one.
    """
    cached_ts = _now_playing_cache.get("timestamp", float("-inf"))
    if monotonic() - cached_ts <= cache_ttl:
        return copy.deepcopy(_now_playing_cache.get("sessions", []))
    return None


def _fetch_now_playing_all_servers() -> list[dict]:
    """Ask all servers for their sessions in parallel, with short timeouts.

    ``now_playing()`` of a client can read the DB (Audiobookshelf reads the
    local user names). That is safe: each worker has its own app context and
    session. The clients are made here, in the calling thread.
    """
    servers_info: list[tuple[int, str, str]] = []
    jobs: list[Callable[[], Any]] = []

    for server in db.session.query(MediaServer).all():
        try:
            client = get_client_for_media_server(server)
        except Exception as exc:
            logging.warning(
                f"Failed to get now playing from server {server.name} ({server.server_type}): {exc}"
            )
            continue
        client.timeout = NOW_PLAYING_TIMEOUT
        servers_info.append((server.id, server.name, server.server_type))
        jobs.append(client.now_playing)

    all_sessions: list[dict] = []
    results = run_parallel(jobs, deadline=NOW_PLAYING_DEADLINE)
    for (server_id, name, server_type), (status, value) in zip(
        servers_info, results, strict=True
    ):
        if status != "ok":
            reason = (
                f"no answer within {NOW_PLAYING_DEADLINE:g} s"
                if status == "timeout"
                else value
            )
            logging.warning(
                f"Failed to get now playing from server {name} ({server_type}): {reason}"
            )
            continue

        # Add server information to each session
        for session in value or []:
            session["server_name"] = name
            session["server_type"] = server_type
            session["server_id"] = server_id
            all_sessions.append(session)

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
        client.timeout = NOW_PLAYING_TIMEOUT
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

        # Keep an existing Identity (it may carry a nickname) whichever
        # account in the group holds it.
        existing = next((u.identity for u in same if u.identity), None)
        identity = existing or Identity(
            primary_email=same[0].email,
            primary_username=same[0].username,
        )
        db.session.add(identity)
        db.session.flush()

        for u in same:
            u.identity_id = identity.id

    db.session.commit()


def list_users_all_servers():
    """Return users for all servers (mapping server -> list).

    This always runs the remote sync. Use ``sync_users`` for a throttled sync.
    """
    _auto_link_identities()
    res = {}
    for server in db.session.query(MediaServer).all():
        try:
            res[server.id] = list_users_for_server(server)
        except Exception:
            res[server.id] = []
    return res


# ---------------------------------------------------------------------------
# User sync throttle
# ---------------------------------------------------------------------------


def _user_sync_fingerprint(server: MediaServer) -> tuple:
    """Return the values that identify a server for the sync throttle.

    When the type, URL or key of a server changes, an earlier sync does not
    count any more.
    """
    return (server.server_type, server.url, server.api_key)


def _record_user_sync(server_id: int, fingerprint: tuple) -> None:
    with _user_sync_state_lock:
        _user_sync_done[server_id] = (monotonic(), fingerprint)


def _last_user_sync(server_id: int, fingerprint: tuple) -> float | None:
    """Return the monotonic time of the last successful sync, or None."""
    with _user_sync_state_lock:
        entry = _user_sync_done.get(server_id)
    if entry is None or entry[1] != fingerprint:
        return None
    return entry[0]


def _user_sync_lock(server_id: int) -> threading.Lock:
    with _user_sync_state_lock:
        lock = _user_sync_server_locks.get(server_id)
        if lock is None:
            lock = _user_sync_server_locks[server_id] = threading.Lock()
        return lock


def _sync_server_users(server: MediaServer, *, force: bool, max_age: float) -> bool:
    """Sync the users of one server if needed. Return True if the sync ran."""
    server_id = server.id
    server_name = server.name
    fingerprint = _user_sync_fingerprint(server)
    requested_at = monotonic()

    last = _last_user_sync(server_id, fingerprint)
    if not force and last is not None and requested_at - last < max_age:
        return False

    with _user_sync_lock(server_id):
        # Another caller can have synced this server while this one waited
        # for the lock. Then the data is new enough, also for a forced sync.
        last = _last_user_sync(server_id, fingerprint)
        if last is not None and (
            last >= requested_at or (not force and requested_at - last < max_age)
        ):
            return False

        try:
            list_users_for_server(server)
        except Exception as exc:
            logging.warning("User sync failed for server %s: %s", server_name, exc)
            db.session.rollback()
            return False
        return True


def sync_users(
    server: MediaServer | None = None,
    *,
    force: bool = False,
    max_age: float = USER_SYNC_MAX_AGE,
) -> bool:
    """Sync users from the media server(s) when the local copy is old.

    The remote sync of a server runs only when ``force`` is True, or when the
    last successful sync of that server is older than ``max_age`` seconds.
    The times are kept in process memory. A lock for each server makes sure
    that two concurrent callers do not sync the same server two times.

    Args:
        server: The server to sync. None syncs all servers.
        force: Sync even when the last sync is recent.
        max_age: Maximum age in seconds of the last sync.

    Returns:
        True if a remote sync ran for at least one server.
    """
    servers = [server] if server is not None else db.session.query(MediaServer).all()

    ran = False
    for srv in servers:
        if _sync_server_users(srv, force=force, max_age=max_age):
            ran = True

    if ran:
        _auto_link_identities()
    return ran


def invalidate_server_caches(server_id: int | None = None) -> None:
    """Forget the cached state of one server, or of all servers.

    Call this when a server is created, edited or deleted. The next user sync
    of that server runs, and the next health and now-playing calls fetch new
    data. The image proxy forgets the old origin and auth headers of the
    server, and the next Plex call makes a new connection.
    """
    # Local imports: plex.py imports this module.
    from app.services.image_proxy import ImageProxyService
    from app.services.media.plex import clear_plex_connection_cache

    with _user_sync_state_lock:
        if server_id is None:
            _user_sync_done.clear()
        else:
            _user_sync_done.pop(server_id, None)

    with _health_cache_lock:
        if server_id is None:
            _health_cache.clear()
        else:
            _health_cache.pop(server_id, None)

    _now_playing_cache["timestamp"] = float("-inf")

    ImageProxyService.forget_server(server_id)
    # The Plex cache keys are (url, token). The old values of an edited
    # server are not known here, so clear all entries. This is cheap: each
    # Plex server connects again one time on its next call.
    clear_plex_connection_cache()


# ---------------------------------------------------------------------------
# Server health
# ---------------------------------------------------------------------------


def _health_fingerprint(server: MediaServer) -> tuple:
    return (server.name, server.server_type, server.url, server.api_key)


def _health_error(server_id: int, name: str, server_type: str, error: str) -> dict:
    """Return the health dict for a server that failed."""
    return {
        "error": error,
        "server_name": name,
        "server_type": server_type,
        "server_id": server_id,
        "user_stats": {"total_users": 0, "active_sessions": 0},
        "server_stats": {"version": "Unknown", "transcoding_sessions": 0},
        "library_stats": {},
        "content_stats": {},
    }


def _fetch_server_health(servers: list[MediaServer]) -> dict[int, dict]:
    """Check the given servers in parallel, with short timeouts."""
    health: dict[int, dict] = {}
    servers_info: list[tuple[int, str, str]] = []
    jobs: list[Callable[[], Any]] = []

    for server in servers:
        server_id, name, server_type = server.id, server.name, server.server_type
        try:
            client = get_client_for_media_server(server)
        except Exception as exc:
            health[server_id] = _health_error(
                server_id, name, server_type, f"Failed to get health: {exc!s}"
            )
            continue
        client.timeout = HEALTH_TIMEOUT
        servers_info.append((server_id, name, server_type))
        jobs.append(client.get_readonly_statistics)

    results = run_parallel(jobs, deadline=HEALTH_DEADLINE)
    for (server_id, name, server_type), (status, value) in zip(
        servers_info, results, strict=True
    ):
        if status == "ok":
            stats = value
            stats["server_name"] = name
            stats["server_type"] = server_type
            stats["server_id"] = server_id
            health[server_id] = stats
        elif status == "error":
            health[server_id] = _health_error(
                server_id, name, server_type, f"Failed to get health: {value!s}"
            )
        else:
            health[server_id] = _health_error(
                server_id,
                name,
                server_type,
                f"Failed to get health: no answer within {HEALTH_DEADLINE:g} s",
            )

    return health


def get_all_server_health(*, use_cache: bool = True) -> dict[int, dict]:
    """Return lightweight health statistics for all servers.

    This does not run a user sync. Servers are checked in parallel with short
    timeouts. A result (also a failure) stays in the cache for
    ``HEALTH_CACHE_TTL`` seconds.

    Returns:
        {server_id: stats}. Each stats dict has the keys server_name,
        server_type, server_id, user_stats, server_stats, library_stats and
        content_stats, and error when the check failed.
    """
    servers = db.session.query(MediaServer).all()
    fingerprints = {server.id: _health_fingerprint(server) for server in servers}
    server_ids = [server.id for server in servers]

    def _from_cache() -> tuple[dict[int, dict], list[MediaServer]]:
        now = monotonic()
        fresh: dict[int, dict] = {}
        stale: list[MediaServer] = []
        with _health_cache_lock:
            for server in servers:
                entry = _health_cache.get(server.id)
                if (
                    use_cache
                    and entry is not None
                    and entry["fingerprint"] == fingerprints[server.id]
                    and now - entry["timestamp"] < HEALTH_CACHE_TTL
                ):
                    fresh[server.id] = copy.deepcopy(entry["data"])
                else:
                    stale.append(server)
        return fresh, stale

    health, stale = _from_cache()
    if stale:
        with _health_fetch_lock:
            # Another caller can have checked these servers while this one
            # waited for the lock.
            health, stale = _from_cache()
            fetched = _fetch_server_health(stale)
            now = monotonic()
            with _health_cache_lock:
                for server_id, data in fetched.items():
                    _health_cache[server_id] = {
                        "timestamp": now,
                        "fingerprint": fingerprints[server_id],
                        "data": copy.deepcopy(data),
                    }
                # Forget servers that do not exist any more.
                for server_id in list(_health_cache):
                    if server_id not in fingerprints:
                        del _health_cache[server_id]
            health.update(fetched)

    return {server_id: health[server_id] for server_id in server_ids}
