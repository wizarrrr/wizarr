import datetime
import logging

from app.extensions import db
from app.models import User
from app.services.media.service import delete_user  # facade (Plex / Jellyfin aware)


def delete_user_if_expired() -> list[int]:
    """
    Find users whose `expires` < now, delete them from the media server
    *and* from the Wizarr DB.  Returns a list of db IDs that were removed.
    """
    now = datetime.datetime.now()
    # SQLAlchemy version of: User.select().where(User.expires.is_null(False) & (User.expires < now))
    expired_rows = User.query.filter(
        User.expires.is_not(None),  # not null
        User.expires < now,
    ).all()

    deleted: list[int] = []
    for user in expired_rows:
        try:
            # remove from Plex/Jellyfin + Ombi
            delete_user(user.id)
            # now delete from our SQL database too:
            db.session.delete(user)
            db.session.commit()

            deleted.append(user.id)
        except Exception as exc:
            db.session.rollback()
            logging.error("Failed to delete expired user %s – %s", user.id, exc)

    return deleted
