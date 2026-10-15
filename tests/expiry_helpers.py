"""Shared setup for the expiry tests."""

import datetime

from app.models import MediaServer, Settings, User


def add_expired_users(session, *, action=None, count=1, server_type="jellyfin"):
    """Add users that expired yesterday and return their ids.

    The users are on one new media server of type ``server_type``. When
    ``server_type`` is None, the users have no server. When ``action`` is set,
    it is stored as the "expiry_action" setting. The user tokens are
    "remote-0", "remote-1", and so on.
    """
    server_id = None
    if server_type is not None:
        server = MediaServer(
            name="Server", server_type=server_type, url="http://server", api_key="k"
        )
        session.add(server)
        session.flush()
        server_id = server.id
    expires = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
    users = [
        User(
            token=f"remote-{i}",
            username=f"user{i}",
            email=f"user{i}@example.com",
            code="EXPIRED",
            expires=expires,
            server_id=server_id,
        )
        for i in range(count)
    ]
    session.add_all(users)
    if action is not None:
        session.add(Settings(key="expiry_action", value=action))
    session.commit()
    return [user.id for user in users]
