"""
Audiobookrequest companion client implementation.
"""

import logging

import requests

from app.models import Connection

from .base import CompanionClient


class AudiobookrequestClient(CompanionClient):
    """Client for integrating with Audiobookrequest."""

    @property
    def requires_api_call(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return "Audiobookrequest"

    def invite_user(
        self, username: str, email: str, connection: Connection, password: str = ""
    ) -> dict[str, str]:
        """
        Invite a user to Audiobookrequest.

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
            # Create user in Audiobookrequest
            resp = requests.post(
                f"{connection.url}/api/users",
                headers={
                    "Authorization": f"Bearer {connection.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "username": username,
                    "password": password
                    or "temporary_password_123",  # Use provided password or fallback
                    "email": email,
                    "group": "untrusted",  # Default group (untrusted, trusted, or admin)
                    "root": False,  # Not root user
                },
                timeout=10,
            )

            if resp.status_code in [200, 201]:
                logging.info(
                    "Audiobookrequest user creation for %s → %s",
                    username,
                    resp.status_code,
                )
                return {
                    "status": "success",
                    "message": f"User invited to {connection.name}",
                }
            logging.warning(
                "Audiobookrequest user creation failed for %s → %s: %s",
                username,
                resp.status_code,
                resp.text,
            )
            return {
                "status": "error",
                "message": f"Failed to invite user to {connection.name}: HTTP {resp.status_code}",
            }
        except Exception as exc:
            logging.error(
                "Audiobookrequest user creation error for %s: %s", username, exc
            )
            return {
                "status": "error",
                "message": f"Error inviting user to {connection.name}: {str(exc)}",
            }

    def delete_user(self, username: str, connection: Connection) -> dict[str, str]:
        """
        Delete a user from Audiobookrequest.

        Args:
            username: Username to delete
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        if not connection.url or not connection.api_key:
            return {"status": "error", "message": "Connection missing URL or API key"}

        try:
            # Delete user directly (API returns 404 if user not found)
            resp = requests.delete(
                f"{connection.url}/api/users/{username}",
                headers={"Authorization": f"Bearer {connection.api_key}"},
                timeout=5,
            )

            if resp.status_code == 404:
                return {
                    "status": "warning",
                    "message": f"User {username} not found in {connection.name}",
                }

            if resp.status_code == 204:
                logging.info(
                    "Audiobookrequest delete user %s from %s → %s",
                    username,
                    connection.name,
                    resp.status_code,
                )
                return {
                    "status": "success",
                    "message": f"User deleted from {connection.name}",
                }

            logging.warning(
                "Audiobookrequest delete user failed for %s from %s → %s",
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
                "Audiobookrequest delete user error for %s from %s: %s",
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
        Test the connection to Audiobookrequest.

        Args:
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        if not connection.url or not connection.api_key:
            return {"status": "error", "message": "URL and API key are required"}

        try:
            # Test connection by getting current user info (simple auth test)
            resp = requests.get(
                f"{connection.url}/api/users/me",
                headers={"Authorization": f"Bearer {connection.api_key}"},
                timeout=10,
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "success",
                    "message": f"Connection successful (authenticated as: {data.get('username', 'unknown')})",
                }
            if resp.status_code == 401:
                return {
                    "status": "error",
                    "message": "Invalid API key or token expired",
                }
            if resp.status_code == 403:
                return {
                    "status": "error",
                    "message": "API key does not have sufficient permissions",
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
