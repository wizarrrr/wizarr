import logging

import requests

from app.models import Connection, Settings, User
from app.services.companions import get_companion_client

__all__ = [
    "run_user_importer",
    "delete_user",
    "invite_user_to_connections",
    "delete_user_from_connections",
    "get_connection_for_server",
]


def _cfg():
    """Fetch Ombi/Overseerr URL and API key from the DB (legacy fallback)."""
    url_row = Settings.query.filter_by(key="overseerr_url").first()
    key_row = Settings.query.filter_by(key="ombi_api_key").first()
    return (
        url_row.value if url_row else None,
        key_row.value if key_row else None,
    )


def get_connection_for_server(
    server_id: int, connection_type: str = "ombi"
) -> Connection | None:
    """Get the connection configuration for a specific media server."""
    return Connection.query.filter_by(
        media_server_id=server_id, connection_type=connection_type
    ).first()


def invite_user_to_connections(
    username: str, email: str, server_id: int, password: str = ""
) -> list[dict]:
    """
    Invite a user to all connected external services for the given media server.

    Args:
        username: Username of the user to invite
        email: Email address of the user
        server_id: Media server ID to check for connections
        password: Password for the user (optional, defaults to empty string)

    Returns:
        List of results with connection details and success status
    """
    results = []

    # Get all connections for this server
    connections = Connection.query.filter_by(media_server_id=server_id).all()

    for connection in connections:
        try:
            # Get the appropriate companion client for this connection type
            client_class = get_companion_client(connection.connection_type)
            client = client_class()

            # Use the client to invite the user
            result = client.invite_user(username, email, connection, password)
            results.append(
                {
                    "connection_name": connection.name,
                    "connection_type": connection.connection_type,
                    "status": result["status"],
                    "message": result["message"],
                }
            )
        except ValueError as exc:
            # Unknown connection type
            logging.error(
                "Unknown connection type %s: %s", connection.connection_type, exc
            )
            results.append(
                {
                    "connection_name": connection.name,
                    "connection_type": connection.connection_type,
                    "status": "error",
                    "message": f"Unknown connection type: {connection.connection_type}",
                }
            )

    return results


def run_user_importer(name: str):
    """Legacy function - now uses fallback global settings."""
    url, key = _cfg()
    if not url or not key:
        return None

    try:
        resp = requests.post(
            f"{url}/api/v1/Job/{name}UserImporter/",
            headers={"ApiKey": key},
            timeout=5,
        )
        logging.info("Ombi importer %s → %s", name, resp.status_code)
        return resp
    except Exception as exc:
        logging.error("Ombi importer error: %s", exc)


def run_all_importers():
    """Legacy function - runs importer using global settings."""
    run_user_importer("jellyfin")  # extend when plex/emby needed


def delete_user_from_connections(internal_token: str) -> list[dict]:
    """
    Delete a user from all connected external services.

    Args:
        internal_token: User's internal token

    Returns:
        List of results with connection details and success status
    """
    results = []

    # Get the user
    wiz_user = User.query.filter_by(token=internal_token).first()
    if not wiz_user:
        return [{"status": "error", "message": "User not found"}]

    # Get server ID if available
    server_id = getattr(wiz_user, "server_id", None)
    if not server_id:
        # Try to find connections across all servers for this user
        connections = Connection.query.all()
    else:
        # Get connections for user's server
        connections = Connection.query.filter_by(media_server_id=server_id).all()

    for connection in connections:
        try:
            # Get the appropriate companion client for this connection type
            client_class = get_companion_client(connection.connection_type)
            client = client_class()

            # Use the client to delete the user
            result = client.delete_user(wiz_user.username, connection)
            results.append(
                {
                    "connection_name": connection.name,
                    "connection_type": connection.connection_type,
                    "status": result["status"],
                    "message": result["message"],
                }
            )
        except ValueError as exc:
            # Unknown connection type
            logging.error(
                "Unknown connection type %s: %s", connection.connection_type, exc
            )
            results.append(
                {
                    "connection_name": connection.name,
                    "connection_type": connection.connection_type,
                    "status": "error",
                    "message": f"Unknown connection type: {connection.connection_type}",
                }
            )

    return results


def delete_user(internal_token: str):
    """Legacy function - now uses fallback global settings."""
    url, key = _cfg()
    if not url or not key:
        return None

    # 1. Get Ombi user list
    try:
        users = requests.get(
            f"{url}/api/v1/Identity/Users",
            headers={"ApiKey": key},
            timeout=5,
        ).json()
    except Exception as exc:
        logging.error("Ombi list users failed: %s", exc)
        return None

    # 2. Map our internal token → User → Ombi ID
    wiz_user = User.query.filter_by(token=internal_token).first()
    if not wiz_user:
        return None

    ombi_id = next(
        (u["id"] for u in users if u.get("userName") == wiz_user.username), None
    )

    if ombi_id:
        try:
            resp = requests.delete(
                f"{url}/api/v1/Identity/{ombi_id}",
                headers={"ApiKey": key},
                timeout=5,
            )
            logging.info("Ombi delete user %s → %s", ombi_id, resp.status_code)
            return resp
        except Exception as exc:
            logging.error("Ombi delete user error: %s", exc)
    return None
