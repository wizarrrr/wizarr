"""Facade that dispatches media user management to Plex or Jellyfin."""

from app.extensions import db
from app.models import Settings, User, MediaServer
from .client_base import CLIENTS


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


def get_client(server_type: str | None = None, url: str | None = None, token: str | None = None, server_id: int | None = None):
    """
    Instantiate the MediaClient for the given server_type, optionally overriding URL/token.
    """
    if server_id is not None:
        server = MediaServer.query.get(server_id)
        if not server:
            raise ValueError("Server not found")
        server_type = server.server_type
        url = server.server_url
        token = server.api_key
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


def list_users(clear_cache: bool = False, server_id: int | None = None):
    """
    Return current users from the configured media server, syncing local DB as needed.
    """
    client = get_client(server_id=server_id)
    # clear cache on clients that support it
    if clear_cache and hasattr(client, 'list_users') and hasattr(client.list_users, 'cache_clear'):
        client.list_users.cache_clear()
    return client.list_users()


def delete_user(db_id: int, server_id: int | None = None) -> None:
    """
    Delete a user on the configured media server and remove from local DB.
    """
    client = get_client(server_id=server_id)
    # clear cache pre- and post-removal if supported
    if hasattr(client, 'list_users') and hasattr(client.list_users, 'cache_clear'):
        client.list_users.cache_clear()

    # lookup local record and perform remote deletion
    user = db.session.get(User, db_id)
    if user:
        target_server_id = server_id or user.server_id
        server = MediaServer.query.get(target_server_id) if target_server_id else None
        server_type = server.server_type if server else _mode()
        if server_type == 'plex':
            email = user.email
            if email and email != 'None':
                client.delete_user(email)
        else:
            client.delete_user(user.token)
        # remove local record
        db.session.delete(user)
        db.session.commit()

    if hasattr(client, 'list_users') and hasattr(client.list_users, 'cache_clear'):
        client.list_users.cache_clear()


def scan_libraries(url: str | None = None, token: str | None = None, server_type: str | None = None, server_id: int | None = None):
    """
    Fetch available libraries from the media server, given optional credentials or using Settings.
    Returns a mapping of external_id -> display_name.
    """
    client = get_client(server_type, url, token, server_id=server_id)
    return client.libraries()