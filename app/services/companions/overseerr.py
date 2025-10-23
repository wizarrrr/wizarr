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
        self, _username: str, _email: str, _connection: Connection, _password: str = ""
    ) -> dict[str, str]:
        """
        Overseerr connections are info-only, no actual API calls needed.

        Args:
            _username: Username to invite (unused - info-only)
            _email: Email address (unused - info-only)
            _connection: Connection object with URL and API key (unused - info-only)
            _password: Password for the user (unused - info-only)

        Returns:
            Dict with 'status' and 'message' keys
        """
        return {
            "status": "info_only",
            "message": "Overseerr auto-imports users automatically",
        }

    def delete_user(self, _username: str, _connection: Connection) -> dict[str, str]:
        """
        Overseerr connections are info-only, no deletion needed.

        Args:
            _username: Username to delete (unused - info-only)
            _connection: Connection object with URL and API key (unused - info-only)

        Returns:
            Dict with 'status' and 'message' keys
        """
        return {
            "status": "info_only",
            "message": "Overseerr users managed automatically",
        }

    def test_connection(self, _connection: Connection) -> dict[str, str]:
        """
        Test connection for Overseerr (info-only).

        Args:
            _connection: Connection object with URL and API key (unused - info-only)

        Returns:
            Dict with 'status' and 'message' keys
        """
        return {
            "status": "info_only",
            "message": "Overseerr connections are informational only - no API testing required",
        }
