"""
Overseerr/Jellyseerr companion client implementation.
"""

from app.models import Connection

from .base import CompanionClient


class OverseerrClient(CompanionClient):
    """Client for integrating with Overseerr/Jellyseerr (info-only)."""

    @property
    def requires_api_call(self) -> bool:
        return False

    @property
    def display_name(self) -> str:
        return "Overseerr/Jellyseerr"

    def invite_user(
        self, username: str, email: str, connection: Connection, password: str = ""
    ) -> dict[str, str]:
        """
        Overseerr connections are info-only, no actual API calls needed.

        Args:
            username: Username to invite
            email: Email address
            connection: Connection object with URL and API key
            password: Password for the user (optional, defaults to empty string)

        Returns:
            Dict with 'status' and 'message' keys
        """
        return {
            "status": "info_only",
            "message": "Overseerr auto-imports users automatically",
        }

    def delete_user(self, username: str, connection: Connection) -> dict[str, str]:
        """
        Overseerr connections are info-only, no deletion needed.

        Args:
            username: Username to delete
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        return {
            "status": "info_only",
            "message": "Overseerr users managed automatically",
        }

    def test_connection(self, connection: Connection) -> dict[str, str]:
        """
        Test connection for Overseerr (info-only).

        Args:
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        return {
            "status": "info_only",
            "message": "Overseerr connections are informational only - no API testing required",
        }
