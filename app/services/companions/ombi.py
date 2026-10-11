"""
Ombi companion client implementation.
"""

import logging
import threading
import time

import requests
import requests.exceptions

from app.models import Connection
from app.services.media.client_base import get_http_session

from .base import CompanionClient

# The Ombi user list is cached for a short time for each connection, so that a
# batch of deletions (for example the expiry job) downloads it one time, not
# one time for each user.
USER_LIST_TTL = 60.0  # seconds

# (connection id, url, api key) -> (monotonic time, list of Ombi users)
_user_list_cache: dict[tuple, tuple[float, list[dict]]] = {}
_user_list_lock = threading.Lock()


def _user_list_key(connection: Connection) -> tuple:
    return (connection.id, (connection.url or "").rstrip("/"), connection.api_key)


def invalidate_user_list_cache(connection: Connection | None = None) -> None:
    """Forget the cached Ombi user list of one connection, or of all."""
    with _user_list_lock:
        if connection is None:
            _user_list_cache.clear()
        else:
            _user_list_cache.pop(_user_list_key(connection), None)


def _forget_cached_user(connection: Connection, ombi_user_id) -> None:
    """Remove one deleted user from the cached list, and keep the rest."""
    key = _user_list_key(connection)
    with _user_list_lock:
        entry = _user_list_cache.get(key)
        if entry is not None:
            fetched_at, users = entry
            _user_list_cache[key] = (
                fetched_at,
                [u for u in users if u.get("id") != ombi_user_id],
            )


def _get_ombi_users(connection: Connection) -> list[dict]:
    """Return the Ombi user list, from the cache when it is recent."""
    key = _user_list_key(connection)
    with _user_list_lock:
        entry = _user_list_cache.get(key)
        if entry is not None and time.monotonic() - entry[0] < USER_LIST_TTL:
            return entry[1]

    users = (
        get_http_session()
        .get(
            f"{connection.url}/api/v1/Identity/Users",
            headers={"ApiKey": connection.api_key},
            timeout=5,
        )
        .json()
    )
    if not isinstance(users, list):
        raise ValueError("Unexpected Ombi user list response")

    with _user_list_lock:
        _user_list_cache[key] = (time.monotonic(), users)
    return users


class OmbiClient(CompanionClient):
    """Client for integrating with Ombi."""

    @property
    def requires_api_call(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return "Ombi"

    def invite_user(
        self,
        username: str,
        email: str,
        connection: Connection,
        password: str = "",  # noqa: ARG002
    ) -> dict[str, str]:
        """
        Invite a user to Ombi.

        Args:
            username: Username to invite
            email: Email address
            connection: Connection object with URL and API key
            password: Password for the user (unused - Ombi generates passwords)

        Returns:
            Dict with 'status' and 'message' keys
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
                # The cached user list does not have the new user.
                invalidate_user_list_cache(connection)
                logging.info(
                    "Ombi user creation for %s → %s", username, resp.status_code
                )
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
                "message": f"Error inviting user to {connection.name}: {exc!s}",
            }

    def delete_user(self, username: str, connection: Connection) -> dict[str, str]:
        """
        Delete a user from Ombi.

        Args:
            username: Username to delete
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        if not connection.url or not connection.api_key:
            return {"status": "error", "message": "Connection missing URL or API key"}

        try:
            # 1. Get Ombi user list (cached for a short time)
            users = _get_ombi_users(connection)

            # 2. Find user by username
            ombi_user = next((u for u in users if u.get("userName") == username), None)

            if not ombi_user:
                return {
                    "status": "warning",
                    "message": f"User {username} not found in {connection.name}",
                }

            # 3. Delete user
            resp = get_http_session().delete(
                f"{connection.url}/api/v1/Identity/{ombi_user['id']}",
                headers={"ApiKey": connection.api_key},
                timeout=5,
            )

            if resp.status_code in [200, 204]:
                # Keep the cached list correct for the next deletion.
                _forget_cached_user(connection, ombi_user["id"])
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
            # The cached list can be wrong. Download it again next time.
            invalidate_user_list_cache(connection)
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
                "Ombi delete user error for %s from %s: %s",
                username,
                connection.name,
                exc,
            )
            return {
                "status": "error",
                "message": f"Error deleting user from {connection.name}: {exc!s}",
            }

    def test_connection(self, connection: Connection) -> dict[str, str]:
        """
        Test the connection to Ombi.

        Args:
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        if not connection.url or not connection.api_key:
            return {"status": "error", "message": "URL and API key are required"}

        try:
            # Test connection by getting Ombi settings/about info
            resp = requests.get(
                f"{connection.url}/api/v1/Settings/about",
                headers={"ApiKey": connection.api_key},
                timeout=10,
            )

            if resp.status_code == 200:
                return {
                    "status": "success",
                    "message": "Connection successful",
                }
            if resp.status_code == 401:
                return {
                    "status": "error",
                    "message": "Invalid API key",
                }
            return {
                "status": "error",
                "message": f"Connection failed: HTTP {resp.status_code}",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "message": "Cannot connect to server. Check URL.",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "message": "Connection timeout. Server may be slow or unreachable.",
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Connection test failed: {exc!s}",
            }
