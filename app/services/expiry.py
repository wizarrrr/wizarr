import contextlib
import datetime
import functools
import logging
import os
import threading
import time
from pathlib import Path

from app.extensions import db
from app.models import ExpiredUser, Invitation, User, invitation_servers
from app.services.media.service import delete_user, disable_user

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

EXPIRY_LOCK_FILENAME = "wizarr-expiry.lock"
_expiry_thread_lock = threading.Lock()


def calculate_user_expiry(
    invitation: Invitation, server_id: int | None = None
) -> datetime.datetime | None:
    """
    Calculate when a user should expire based on the invitation's duration.

    If server_id is provided, checks for server-specific expiry first,
    then falls back to invitation-level expiry.

    Args:
        invitation: The invitation used to create the user
        server_id: Optional server ID to check for server-specific expiry

    Returns:
        datetime.datetime | None: The expiry date, or None if no expiry
    """
    # Check for server-specific expiry first
    if server_id:
        server_expiry = get_server_specific_expiry(invitation.id, server_id)
        if server_expiry:
            return server_expiry

    # Fall back to invitation-level duration
    if not invitation.duration:
        return None

    try:
        days = int(invitation.duration)
        return datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days)
    except (ValueError, TypeError):
        logging.warning(
            f"Invalid duration '{invitation.duration}' for invitation {invitation.id}"
        )
        return None


def get_server_specific_expiry(
    invitation_id: int, server_id: int
) -> datetime.datetime | None:
    """
    Get server-specific expiry date for an invitation-server combination.

    Args:
        invitation_id: The invitation ID
        server_id: The server ID

    Returns:
        datetime.datetime | None: The server-specific expiry date, or None
    """
    result = db.session.execute(
        invitation_servers.select().where(
            (invitation_servers.c.invite_id == invitation_id)
            & (invitation_servers.c.server_id == server_id)
        )
    ).first()

    return result.expires if result else None


def set_server_specific_expiry(
    invitation_id: int, server_id: int, expires: datetime.datetime | None
) -> None:
    """
    Set server-specific expiry date for an invitation-server combination.

    Args:
        invitation_id: The invitation ID
        server_id: The server ID
        expires: The expiry date to set, or None to clear
    """
    db.session.execute(
        invitation_servers.update()
        .where(
            (invitation_servers.c.invite_id == invitation_id)
            & (invitation_servers.c.server_id == server_id)
        )
        .values(expires=expires)
    )
    db.session.commit()


@contextlib.contextmanager
def _expiry_run_lock():
    """Let only one expiry run work at a time, in all processes.

    The history row is committed before the remote calls, so it cannot stop
    a second run that starts at the same time. The scheduled job runs in the
    background leader, but an admin can start a run from any worker.

    Yields True when this run has the lock. The lock file stays in the
    database directory. The operating system releases the lock when the file
    closes or the process stops.
    """
    if not _expiry_thread_lock.acquire(blocking=False):
        yield False
        return

    fd = None
    try:
        if fcntl is not None:
            from app.config import DATABASE_DIR

            try:
                fd = os.open(
                    Path(DATABASE_DIR) / EXPIRY_LOCK_FILENAME,
                    os.O_RDWR | os.O_CREAT,
                    0o600,
                )
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            except OSError as exc:
                logging.warning(
                    "Cannot use the expiry lock file (%s). The run continues.", exc
                )
        yield True
    finally:
        if fd is not None:
            os.close(fd)
        _expiry_thread_lock.release()


def _one_expiry_run_at_a_time(func):
    """Skip the run when another expiry run is active."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with _expiry_run_lock() as acquired:
            if not acquired:
                logging.info(
                    "Another expiry run is active. %s does nothing.", func.__name__
                )
                return []
            return func(*args, **kwargs)

    return wrapper


def _record_expiry_event(user: User) -> ExpiredUser | None:
    """Reuse history when an expired account was enabled without extending expiry.

    Returns the new ExpiredUser row, or None when the history row exists.
    """
    existing = ExpiredUser.query.filter_by(
        original_user_id=user.id, expired_at=user.expires
    ).first()
    if existing is not None:
        return None

    event = ExpiredUser(
        original_user_id=user.id,
        username=user.username,
        email=user.email,
        invitation_code=user.code,
        server_id=user.server_id,
        expired_at=user.expires,
        deleted_at=datetime.datetime.now(datetime.UTC),
    )
    db.session.add(event)
    # A concurrent insertion must still abort this worker's claim before any
    # media operation; do not treat a uniqueness failure as reusable history.
    db.session.flush()
    return event


def _claim_expiry(user: User) -> tuple[bool, int | None]:
    """Record the expiry event in one short transaction of its own.

    The unique history row is the claim: when another worker processes the
    same user at the same time, its insert fails here, before any media
    operation. The transaction ends before the remote calls, so the SQLite
    write lock is not held while we wait for a media server.

    Returns (claimed, new_event_id). ``new_event_id`` is None when the history
    row existed before (an expired user that was enabled again).
    """
    user_id = user.id
    try:
        event = _record_expiry_event(user)
        # The flush gave the row its id. Read it before the commit expires it.
        event_id = event.id if event is not None else None
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logging.error(
            "Failed to claim expired user %s – %s. Will retry on next run.",
            user_id,
            exc,
        )
        return False, None
    return True, event_id


def _release_expiry_claim(event_id: int | None) -> None:
    """Remove the history row of a failed attempt, so the next run retries.

    A history row that existed before the attempt is kept.
    """
    if event_id is None:
        return
    try:
        ExpiredUser.query.filter_by(id=event_id).delete()
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logging.error("Failed to remove expiry history %s – %s", event_id, exc)


def _delete_expired_user(user_id: int) -> None:
    """Delete the user remotely, then locally, and commit.

    ``delete_user`` does all remote calls (media server, LDAP, companion
    apps) before its only local write, so no write transaction is open
    during the remote calls. The local delete is one short transaction.
    """
    delete_user(user_id, commit=False, require_remote=True)
    db.session.commit()


@_one_expiry_run_at_a_time
def delete_user_if_expired() -> list[int]:
    """
    Find users whose `expires` < now, delete them from their associated media servers
    and from the Wizarr DB. Returns a list of db IDs that were removed.

    This function is multi-server aware and will delete users from their specific
    servers rather than assuming a single global server.

    No DB write transaction is open during a remote call. For each user:
    a short transaction records the expiry event, the remote deletion runs,
    then a short transaction deletes the local row. When the remote deletion
    fails, the event is removed again and the user is kept for the next run.
    """
    now = datetime.datetime.now(datetime.UTC)
    expired_rows = User.query.filter(
        User.expires.is_not(None),  # not null
        User.expires < now,
    ).all()
    # End the read before the loop. Each step below commits on its own.
    db.session.commit()

    deleted: list[int] = []
    for user in expired_rows:
        try:
            user_id, username = user.id, user.username
        except Exception as exc:
            # The row was removed by another process after the query.
            db.session.rollback()
            logging.info("Expired user is gone already – %s", exc)
            continue

        claimed, event_id = _claim_expiry(user)
        if not claimed:
            continue

        try:
            _delete_expired_user(user_id)
        except Exception as exc:
            # Keep the User record for retry on next scheduler run
            db.session.rollback()
            _release_expiry_claim(event_id)
            logging.error(
                "Failed to delete expired user %s – %s. Will retry on next run.",
                user_id,
                exc,
            )
            continue

        deleted.append(user_id)
        logging.info("🗑️ Expired user %s (%s) logged and deleted", user_id, username)
        # Add delay to prevent hammering the media server's database. No
        # transaction is open here.
        time.sleep(1)

    db.session.commit()
    return deleted


def get_server_disable_capabilities() -> dict[str, bool]:
    """Returns a mapping of server types to whether they support user disabling.

    Returns:
        dict: Server type -> supports disable (True/False)
    """
    return {
        "jellyfin": True,
        "emby": True,  # Inherits from Jellyfin
        "plex": False,  # Only supports deletion via removeFriend()
        "audiobookshelf": True,
        "kavita": True,  # Removes library access
        "komga": True,  # Removes library access
        "romm": True,
        "navidrome": False,  # Not supported
        "drop": False,  # Not supported
    }


def _disable_expired_user(user: User) -> bool:
    """Disable the user remotely, then mark it disabled locally, and commit.

    ``disable_user`` does the remote call first and writes locally only on
    success, so no write transaction is open during the remote call.
    Returns False when the remote disable failed. Then nothing is written.
    """
    if not disable_user(user.id, commit=False):
        db.session.rollback()
        return False
    user.is_disabled = True
    db.session.flush()
    db.session.commit()
    return True


@_one_expiry_run_at_a_time
def disable_or_delete_user_if_expired() -> list[int]:
    """
    Find users whose `expires` < now, and either disable or delete them based on
    the expiry_action setting. Returns a list of db IDs that were processed.

    This function is multi-server aware and will handle users from their specific
    servers rather than assuming a single global server.

    No DB write transaction is open during a remote call. For each user:
    a short transaction records the expiry event, the remote disable or
    deletion runs, then a short transaction writes the local change. When the
    remote action fails, the event is removed again and the user is kept for
    the next run.
    """
    from app.models import Settings

    # Get the expiry action setting, default to delete for backward compatibility
    expiry_action_setting = Settings.query.filter_by(key="expiry_action").first()
    expiry_action = expiry_action_setting.value if expiry_action_setting else "delete"

    now = datetime.datetime.now(datetime.UTC)
    expired_rows = User.query.filter(
        User.expires.is_not(None),  # not null
        User.expires < now,
        User.is_disabled.is_(False),
    ).all()
    # End the read before the loop. Each step below commits on its own.
    db.session.commit()

    capabilities = get_server_disable_capabilities()
    processed: list[int] = []
    for user in expired_rows:
        try:
            user_id, username = user.id, user.username
            server_type = user.server.server_type if user.server else None
        except Exception as exc:
            # The row was removed by another process after the query.
            db.session.rollback()
            logging.info("Expired user is gone already – %s", exc)
            continue

        claimed, event_id = _claim_expiry(user)
        if not claimed:
            continue

        # Determine action based on setting and server capability
        should_disable = (
            expiry_action == "disable"
            and server_type is not None
            and capabilities.get(server_type, False)
        )

        try:
            if should_disable:
                # Try to disable the user using the service function
                try:
                    if not _disable_expired_user(user):
                        raise Exception("Disable operation failed")
                    processed.append(user_id)
                    logging.info(
                        "🔒 Expired user %s (%s) disabled on %s",
                        user_id,
                        username,
                        server_type or "unknown",
                    )
                except Exception as disable_exc:
                    # Keep the account and try again on the next run. Deleting
                    # here would remove a user the admin chose to keep, over a
                    # server that may only have been down for a moment.
                    db.session.rollback()
                    _release_expiry_claim(event_id)
                    logging.warning(
                        "Failed to disable user %s, keeping it for the next run: %s",
                        user_id,
                        disable_exc,
                    )
                    continue
            else:
                # Delete the user (either by setting or server doesn't support disable)
                _delete_expired_user(user_id)
                processed.append(user_id)
                action_reason = (
                    "setting" if expiry_action == "delete" else "unsupported"
                )
                logging.info(
                    "🗑️ Expired user %s (%s) deleted (%s)",
                    user_id,
                    username,
                    action_reason,
                )
        except Exception as exc:
            # Keep the User record for retry on next scheduler run
            db.session.rollback()
            _release_expiry_claim(event_id)
            logging.error(
                "Failed to process expired user %s – %s. Will retry on next run.",
                user_id,
                exc,
            )
            continue

        # Add delay to prevent hammering the media server's database. No
        # transaction is open here.
        time.sleep(1)

    db.session.commit()
    return processed


def cleanup_expired_user_by_email(email: str) -> None:
    """
    Remove expired user entries when a new user with the same email is created.

    Args:
        email: The email address to clean up from expired users
    """
    if not email:
        return

    expired_users = ExpiredUser.query.filter_by(email=email).all()
    for expired_user in expired_users:
        db.session.delete(expired_user)
        logging.info(
            "🔄 Removed expired user record for %s (email: %s) - user re-added",
            expired_user.username,
            email,
        )

    if expired_users:
        db.session.commit()


def get_expired_users() -> list[ExpiredUser]:
    """
    Get all expired users for display in the admin interface.

    Returns:
        List of ExpiredUser objects ordered by deletion date (most recent first)
    """
    return (
        ExpiredUser.query.options(db.joinedload(ExpiredUser.server))
        .order_by(ExpiredUser.deleted_at.desc())
        .all()
    )


def get_expiring_this_week_users() -> list[dict]:
    """
    Get all active users whose expiry date is within the next 7 days.

    Returns:
        List of dictionaries with user data and calculated days left
    """
    now = datetime.datetime.now(datetime.UTC)
    one_week_from_now = now + datetime.timedelta(days=7)

    users = (
        User.query.options(db.joinedload(User.server), db.joinedload(User.identity))
        .filter(
            User.expires.is_not(None),  # Has an expiry date
            User.expires > now,  # Not already expired
            User.expires <= one_week_from_now,  # Expires within a week
        )
        .order_by(User.expires.asc())
        .all()
    )

    # Add calculated days left to each user
    result = []
    for user in users:
        # Ensure user.expires is timezone-aware for comparison
        # Database stores naive UTC, so add timezone info if missing
        user_expires = user.expires
        if user_expires.tzinfo is None:
            user_expires = user_expires.replace(tzinfo=datetime.UTC)

        days_left = (user_expires - now).total_seconds() / 86400
        days_left_int = max(1, round(days_left))  # Ensure it's an integer, minimum 1
        result.append(
            {
                "user": user,
                "days_left": days_left_int,
                "urgency": "critical"
                if days_left <= 1
                else "urgent"
                if days_left <= 3
                else "soon",
            }
        )

    return result
