import logging

import requests

from app.models import Connection, Settings, User

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


def invite_user_to_connections(username: str, email: str, server_id: int) -> list[dict]:
    """
    Invite a user to all connected external services for the given media server.

    Args:
        username: Username of the user to invite
        email: Email address of the user
        server_id: Media server ID to check for connections

    Returns:
        List of results with connection details and success status
    """
    results = []

    # Get all connections for this server
    connections = Connection.query.filter_by(media_server_id=server_id).all()

    for connection in connections:
        if connection.connection_type == "overseerr":
            # Overseerr connections are info-only, no actual API calls needed
            results.append(
                {
                    "connection_name": connection.name,
                    "connection_type": "overseerr",
                    "status": "info_only",
                    "message": "Overseerr auto-imports users automatically",
                }
            )
            continue

        if connection.connection_type == "ombi":
            # Ombi connections require API calls
            result = _invite_user_to_ombi(username, email, connection)
            results.append(
                {
                    "connection_name": connection.name,
                    "connection_type": "ombi",
                    "status": result["status"],
                    "message": result["message"],
                }
            )

    return results


def _invite_user_to_ombi(username: str, email: str, connection: Connection) -> dict:
    """
    Invite a user to a specific Ombi connection.

    Args:
        username: Username to invite
        email: Email address
        connection: Connection object with URL and API key

    Returns:
        Dict with status and message
    """
    if not connection.url or not connection.api_key:
        return {"status": "error", "message": "Connection missing URL or API key"}

    try:
        # Create user in Ombi
        resp = requests.post(
            f"{connection.url}/api/v1/Identity",
            headers={"ApiKey": connection.api_key},
            json={
                "userName": username,
                "email": email,
                "password": "",  # Ombi will generate or user will set via email
                "claims": [
                    {
                        "type": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
                        "value": username,
                    },
                    {
                        "type": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
                        "value": email,
                    },
                ],
            },
            timeout=10,
        )

        if resp.status_code in [200, 201]:
            logging.info("Ombi user creation for %s → %s", username, resp.status_code)
            return {
                "status": "success",
                "message": f"User invited to {connection.name}",
            }
        logging.warning(
            "Ombi user creation failed for %s → %s: %s",
            username,
            resp.status_code,
            resp.text,
        )
        return {
            "status": "error",
            "message": f"Failed to invite user to {connection.name}: HTTP {resp.status_code}",
        }
    except Exception as exc:
        logging.error("Ombi user creation error for %s: %s", username, exc)
        return {
            "status": "error",
            "message": f"Error inviting user to {connection.name}: {str(exc)}",
        }


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
        if connection.connection_type == "overseerr":
            # Overseerr connections are info-only, no deletion needed
            results.append(
                {
                    "connection_name": connection.name,
                    "connection_type": "overseerr",
                    "status": "info_only",
                    "message": "Overseerr users managed automatically",
                }
            )
            continue

        if connection.connection_type == "ombi":
            # Ombi connections require API calls
            result = _delete_user_from_ombi(wiz_user.username, connection)
            results.append(
                {
                    "connection_name": connection.name,
                    "connection_type": "ombi",
                    "status": result["status"],
                    "message": result["message"],
                }
            )

    return results


def _delete_user_from_ombi(username: str, connection: Connection) -> dict:
    """
    Delete a user from a specific Ombi connection.

    Args:
        username: Username to delete
        connection: Connection object with URL and API key

    Returns:
        Dict with status and message
    """
    if not connection.url or not connection.api_key:
        return {"status": "error", "message": "Connection missing URL or API key"}

    try:
        # 1. Get Ombi user list
        users = requests.get(
            f"{connection.url}/api/v1/Identity/Users",
            headers={"ApiKey": connection.api_key},
            timeout=5,
        ).json()

        # 2. Find user by username
        ombi_user = next((u for u in users if u.get("userName") == username), None)

        if not ombi_user:
            return {
                "status": "warning",
                "message": f"User {username} not found in {connection.name}",
            }

        # 3. Delete user
        resp = requests.delete(
            f"{connection.url}/api/v1/Identity/{ombi_user['id']}",
            headers={"ApiKey": connection.api_key},
            timeout=5,
        )

        if resp.status_code in [200, 204]:
            logging.info(
                "Ombi delete user %s from %s → %s",
                username,
                connection.name,
                resp.status_code,
            )
            return {
                "status": "success",
                "message": f"User deleted from {connection.name}",
            }
        logging.warning(
            "Ombi delete user failed for %s from %s → %s",
            username,
            connection.name,
            resp.status_code,
        )
        return {
            "status": "error",
            "message": f"Failed to delete user from {connection.name}: HTTP {resp.status_code}",
        }

    except Exception as exc:
        logging.error(
            "Ombi delete user error for %s from %s: %s", username, connection.name, exc
        )
        return {
            "status": "error",
            "message": f"Error deleting user from {connection.name}: {str(exc)}",
        }


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
