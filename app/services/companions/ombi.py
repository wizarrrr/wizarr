"""
Ombi companion client implementation.
"""

import logging

import requests

from app.models import Connection

from .base import CompanionClient


class OmbiClient(CompanionClient):
    """Client for integrating with Ombi."""

    @property
    def requires_api_call(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return "Ombi"

    def invite_user(
        self, username: str, email: str, connection: Connection, password: str = ""
    ) -> dict[str, str]:
        """
        Invite a user to Ombi.

        Args:
            username: Username to invite
            email: Email address
            connection: Connection object with URL and API key
            password: Password for the user (optional, defaults to empty string)

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
                "message": f"Error inviting user to {connection.name}: {str(exc)}",
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
                "Ombi delete user error for %s from %s: %s",
                username,
                connection.name,
                exc,
            )
            return {
                "status": "error",
                "message": f"Error deleting user from {connection.name}: {str(exc)}",
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
                "message": f"Connection test failed: {str(exc)}",
            }
