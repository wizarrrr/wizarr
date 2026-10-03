import datetime
import logging
import time
from contextlib import suppress

from sqlalchemy.exc import ResourceClosedError, SQLAlchemyError

from app.extensions import db
from app.models import ExpiredUser, Invitation, Settings, User, invitation_servers
from app.services.media.service import delete_user, disable_user

# Display window for the "Recently Expired" panel. Stored in Settings so the
# choice survives a page reload; None means "show the full history".
EXPIRED_WINDOW_SETTING = "expired_users_window_days"
EXPIRED_WINDOW_DEFAULT = 30
EXPIRED_WINDOW_DAY_CHOICES = (30, 60, 90)


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


def delete_user_if_expired() -> list[int]:
    """
    Find users whose `expires` < now, delete them from their associated media servers
    and from the Wizarr DB. Returns a list of db IDs that were removed.

    This function is multi-server aware and will delete users from their specific
    servers rather than assuming a single global server.
    """
    now = datetime.datetime.now(datetime.UTC)
    expired_rows = User.query.filter(
        User.expires.is_not(None),  # not null
        User.expires < now,
    ).all()

    deleted: list[int] = []
    for user in expired_rows:
        # Use a nested transaction (savepoint) so if deletion fails,
        # we can rollback the ExpiredUser creation too
        savepoint = db.session.begin_nested()
        try:
            # Log the user to expired_users table before deletion
            expired_user = ExpiredUser(
                original_user_id=user.id,
                username=user.username,
                email=user.email,
                invitation_code=user.code,
                server_id=user.server_id,
                expired_at=user.expires,
                deleted_at=datetime.datetime.now(datetime.UTC),
            )
            db.session.add(expired_user)
            db.session.flush()  # Ensure it's saved before we delete the user

            # Delete the user (handles server-specific deletion internally)
            delete_user(user.id, commit=False)

            deleted.append(user.id)
            logging.info(
                "🗑️ Expired user %s (%s) logged and deleted", user.id, user.username
            )
            savepoint.commit()  # Commit the savepoint on success
            # Add delay to prevent hammering the media server's database
            time.sleep(1)
        except Exception as exc:
            # Rollback the savepoint - this removes the ExpiredUser record
            # and keeps the User record for retry on next scheduler run
            with suppress(ResourceClosedError):
                savepoint.rollback()
            logging.error(
                "Failed to delete expired user %s – %s. Will retry on next run.",
                user.id,
                exc,
            )

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


def disable_or_delete_user_if_expired() -> list[int]:
    """
    Find users whose `expires` < now, and either disable or delete them based on
    the expiry_action setting. Returns a list of db IDs that were processed.

    This function is multi-server aware and will handle users from their specific
    servers rather than assuming a single global server.
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

    processed: list[int] = []
    for user in expired_rows:
        # Use a nested transaction (savepoint) so if deletion/disabling fails,
        # we can rollback the ExpiredUser creation too
        savepoint = db.session.begin_nested()
        try:
            # Log the user to expired_users table before processing
            expired_user = ExpiredUser(
                original_user_id=user.id,
                username=user.username,
                email=user.email,
                invitation_code=user.code,
                server_id=user.server_id,
                expired_at=user.expires,
                deleted_at=datetime.datetime.now(datetime.UTC),
            )
            db.session.add(expired_user)
            db.session.flush()  # Ensure it's saved before we process the user

            # Determine action based on setting and server capability
            should_disable = (
                expiry_action == "disable"
                and user.server
                and get_server_disable_capabilities().get(
                    user.server.server_type, False
                )
            )

            if should_disable:
                # Try to disable the user using the service function
                try:
                    if disable_user(user.id, commit=False):
                        # Successfully disabled the user
                        user.is_disabled = True
                        db.session.flush()
                        processed.append(user.id)
                        logging.info(
                            "🔒 Expired user %s (%s) disabled on %s",
                            user.id,
                            user.username,
                            user.server.server_type if user.server else "unknown",
                        )
                        savepoint.commit()  # Commit the savepoint on success
                        # Add delay to prevent hammering the media server's database
                        time.sleep(1)
                    else:
                        # Disable failed, fallback to deletion
                        raise Exception("Disable operation failed")
                except Exception as disable_exc:
                    logging.warning(
                        "Failed to disable user %s, falling back to deletion: %s",
                        user.id,
                        disable_exc,
                    )
                    # Fallback to deletion using service function
                    delete_user(user.id, commit=False)
                    processed.append(user.id)
                    logging.info(
                        "🗑️ Expired user %s (%s) deleted (disable fallback)",
                        user.id,
                        user.username,
                    )
                    savepoint.commit()  # Commit the savepoint on success
                    # Add delay to prevent hammering the media server's database
                    time.sleep(1)
            else:
                # Delete the user (either by setting or server doesn't support disable)
                delete_user(user.id, commit=False)
                processed.append(user.id)
                action_reason = (
                    "setting" if expiry_action == "delete" else "unsupported"
                )
                logging.info(
                    "🗑️ Expired user %s (%s) deleted (%s)",
                    user.id,
                    user.username,
                    action_reason,
                )
                savepoint.commit()  # Commit the savepoint on success
                # Add delay to prevent hammering the media server's database
                time.sleep(1)
        except Exception as exc:
            # Rollback the savepoint - this removes the ExpiredUser record
            # and keeps the User record for retry on next scheduler run
            with suppress(ResourceClosedError):
                savepoint.rollback()
            logging.error(
                "Failed to process expired user %s – %s. Will retry on next run.",
                user.id,
                exc,
            )

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


def parse_expired_users_window(raw: str | int | None) -> int | None:
    """
    Coerce a stored or submitted window value onto the allowed choices.

    Accepts an integer number of days, or "all"/"none" for the full history.
    Anything unrecognised falls back to the default rather than raising, so a
    hand-edited setting or a crafted query string cannot break the page.

    Returns:
        Number of days to show, or None for the full history
    """
    if raw is None:
        return EXPIRED_WINDOW_DEFAULT

    text = str(raw).strip().lower()
    if text in {"all", "none"}:
        return None
    if not text:
        return EXPIRED_WINDOW_DEFAULT

    try:
        days = int(text)
    except ValueError:
        return EXPIRED_WINDOW_DEFAULT

    return days if days in EXPIRED_WINDOW_DAY_CHOICES else EXPIRED_WINDOW_DEFAULT


def get_expired_users_window() -> int | None:
    """
    Return the stored display window for the expired-users panel.

    Returns:
        Number of days to show, or None for the full history
    """
    try:
        setting = Settings.query.filter_by(key=EXPIRED_WINDOW_SETTING).first()
    except (RuntimeError, SQLAlchemyError) as exc:
        logging.warning("Failed to load expired-users window setting: %s", exc)
        return EXPIRED_WINDOW_DEFAULT

    if setting is None or setting.value is None:
        return EXPIRED_WINDOW_DEFAULT

    return parse_expired_users_window(setting.value)


def set_expired_users_window(window_days: int | None) -> None:
    """Store the display window for the expired-users panel."""
    value = "all" if window_days is None else str(window_days)
    setting = Settings.query.filter_by(key=EXPIRED_WINDOW_SETTING).first()

    if setting is None:
        db.session.add(Settings(key=EXPIRED_WINDOW_SETTING, value=value))
    else:
        setting.value = value

    db.session.commit()


def has_any_expired_users() -> bool:
    """
    Report whether any expired-user rows exist at all, ignoring the window.

    The bounded panel uses this to keep its window selector reachable: without
    it, a window that filters every row would hide the panel and the control
    needed to widen it again.
    """
    return db.session.query(ExpiredUser.id).first() is not None


def get_expired_users(
    within_days: int | None = EXPIRED_WINDOW_DEFAULT,
) -> list[ExpiredUser]:
    """
    Get expired users for display in the admin interface.

    The panel this feeds is labelled "Recently Expired", so it is bounded by
    default. Rows outside the window are still retained in the table; only the
    display is limited.

    Args:
        within_days: Only include users deleted within this many days. Pass
            None to return the full history.

    Returns:
        List of ExpiredUser objects ordered by deletion date (most recent first)
    """
    query = ExpiredUser.query.options(db.joinedload(ExpiredUser.server))

    if within_days is not None:
        # deleted_at is a naive column holding UTC (see ExpiredUser.deleted_at),
        # so the cutoff is built naive to keep the comparison naive-to-naive.
        now_naive = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        cutoff = now_naive - datetime.timedelta(days=within_days)
        query = query.filter(ExpiredUser.deleted_at >= cutoff)

    return query.order_by(ExpiredUser.deleted_at.desc()).all()


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
