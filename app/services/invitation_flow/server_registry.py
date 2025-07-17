"""
Simple server integration registry for easy extensibility.
"""

import logging
from abc import ABC, abstractmethod

from app.models import MediaServer
from app.services.media.service import get_client_for_media_server


class ServerAccountManager(ABC):
    """Base class for server-specific account management."""

    def __init__(self, server: MediaServer):
        self.server = server
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{server.name}")

    @abstractmethod
    def create_account(
        self, username: str, password: str, email: str, **kwargs
    ) -> tuple[bool, str]:
        """Create user account on the server."""
        pass

    def get_client(self):
        """Get media client for this server."""
        return get_client_for_media_server(self.server)


class PlexAccountManager(ServerAccountManager):
    """Account manager for Plex servers."""

    def create_account(
        self, username: str, password: str, email: str, **kwargs
    ) -> tuple[bool, str]:
        """Create Plex account using OAuth token."""
        try:
            client = self.get_client()
            oauth_token = kwargs.get("oauth_token")

            if not oauth_token:
                return False, "OAuth token required for Plex"

            success, message = client.join(
                username=username,
                password="",  # Not used for Plex OAuth
                email=email,
                code=kwargs.get("invitation_code", ""),
                oauth_token=oauth_token,
            )

            return success, message

        except Exception as e:
            error_msg = f"Failed to create Plex account: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg


class FormBasedAccountManager(ServerAccountManager):
    """Account manager for form-based servers (Jellyfin, Emby, etc.)."""

    def create_account(
        self, username: str, password: str, email: str, **kwargs
    ) -> tuple[bool, str]:
        """Create account using traditional form data."""
        try:
            client = self.get_client()

            success, message = client.join(
                username=username,
                password=password,
                confirm=kwargs.get("confirm_password", password),
                email=email,
                code=kwargs.get("invitation_code", ""),
            )

            return success, message

        except Exception as e:
            error_msg = f"Failed to create {self.server.server_type} account: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg


class ServerIntegrationRegistry:
    """Simple registry for server integrations."""

    # Map server types to account manager classes
    _account_managers: dict[str, type[ServerAccountManager]] = {
        "plex": PlexAccountManager,
        "jellyfin": FormBasedAccountManager,
        "emby": FormBasedAccountManager,
        "audiobookshelf": FormBasedAccountManager,
        "romm": FormBasedAccountManager,
        "kavita": FormBasedAccountManager,
        "komga": FormBasedAccountManager,
    }

    @classmethod
    def get_account_manager(cls, server: MediaServer) -> ServerAccountManager:
        """Get account manager for server."""
        manager_class = cls._account_managers.get(
            server.server_type, FormBasedAccountManager
        )
        return manager_class(server)

    @classmethod
    def register_server_type(
        cls, server_type: str, manager_class: type[ServerAccountManager]
    ):
        """Register a new server type with its account manager."""
        cls._account_managers[server_type] = manager_class

    @classmethod
    def get_supported_server_types(cls) -> list[str]:
        """Get list of supported server types."""
        return list(cls._account_managers.keys())
