"""
Base companion client interface.

Defines the common interface that all companion app clients must implement.
"""

from abc import ABC, abstractmethod

from app.models import Connection


class CompanionClient(ABC):
    """Base class for companion app clients."""

    @abstractmethod
    def invite_user(
        self, username: str, email: str, connection: Connection, password: str = ""
    ) -> dict[str, str]:
        """
        Invite a user to the companion service.

        Args:
            username: Username to invite
            email: Email address
            connection: Connection object with URL and API key
            password: Password for the user (optional, defaults to empty string)

        Returns:
            Dict with 'status' and 'message' keys
        """
        pass

    @abstractmethod
    def delete_user(self, username: str, connection: Connection) -> dict[str, str]:
        """
        Delete a user from the companion service.

        Args:
            username: Username to delete
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        pass

    @property
    @abstractmethod
    def requires_api_call(self) -> bool:
        """Whether this companion type requires actual API calls or is info-only."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for this companion type."""
        pass

    @abstractmethod
    def test_connection(self, connection: Connection) -> dict[str, str]:
        """
        Test the connection to the companion service.

        Args:
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        pass
