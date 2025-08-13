import datetime
import logging

from app.extensions import db
from app.models import ExpiredUser, Invitation, User, invitation_servers
from app.services.media.service import delete_user, delete_user_for_server


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
        return datetime.datetime.now() + datetime.timedelta(days=days)
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
    now = datetime.datetime.now()
    expired_rows = User.query.filter(
        User.expires.is_not(None),  # not null
        User.expires < now,
    ).all()

    deleted: list[int] = []
    for user in expired_rows:
        try:
            # Log the user to expired_users table before deletion
            expired_user = ExpiredUser(
                original_user_id=user.id,
                username=user.username,
                email=user.email,
                invitation_code=user.code,
                server_id=user.server_id,
                expired_at=user.expires,
                deleted_at=datetime.datetime.now(),
            )
            db.session.add(expired_user)
            db.session.flush()  # Ensure it's saved before we delete the user

            # Use server-specific deletion if user has a server_id
            if user.server_id and user.server:
                delete_user_for_server(user.server, user.id)
            else:
                # Fallback to the legacy delete_user function
                delete_user(user.id)

            deleted.append(user.id)
            logging.info(
                "🗑️ Expired user %s (%s) logged and deleted", user.id, user.username
            )
        except Exception as exc:
            logging.error("Failed to delete expired user %s – %s", user.id, exc)

    db.session.commit()
    return deleted


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
    now = datetime.datetime.now()
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
        days_left = (user.expires - now).total_seconds() / 86400
        days_left_int = max(
            1, int(round(days_left))
        )  # Ensure it's an integer, minimum 1
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
