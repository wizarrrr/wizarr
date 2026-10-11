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

    @property
    @abstractmethod
    def requires_api_call(self) -> bool:
        """Whether this companion type requires actual API calls or is info-only."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for this companion type."""

    @abstractmethod
    def test_connection(self, connection: Connection) -> dict[str, str]:
        """
        Test the connection to the companion service.

        Args:
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """

    def provision_plex_user(
        self,
        auth_token: str,  # noqa: ARG002
        connection: Connection,  # noqa: ARG002
    ) -> dict[str, str]:
        """
        Create the user on the companion service using their Plex token.

        Services that sign users in with Plex only create the account on first
        login, so an invited user has no account until they visit and log in by
        hand. Given the token from the Plex OAuth invite, a companion can create
        that account up front instead.

        Only meaningful for Plex; the default is to do nothing so companions that
        provision another way are unaffected.

        Args:
            auth_token: The invited user's Plex auth token
            connection: Connection object with URL and API key

        Returns:
            Dict with 'status' and 'message' keys
        """
        return {
            "status": "not_supported",
            "message": f"{self.display_name} does not provision Plex users",
        }
