"""
Simple authentication strategies for invitation flows.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from flask import session

from app.models import MediaServer


class AuthenticationStrategy(ABC):
    """Base class for authentication strategies."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def authenticate(
        self, servers: list[MediaServer], form_data: dict[str, Any]
    ) -> tuple[bool, str, dict[str, Any]]:
        """
        Perform authentication.

        Returns:
            (success, message, user_data)
        """
        pass

    @abstractmethod
    def get_required_fields(self) -> list[str]:
        """Get list of required form fields."""
        pass


class FormBasedStrategy(AuthenticationStrategy):
    """Strategy for traditional form-based authentication."""

    def authenticate(
        self, servers: list[MediaServer], form_data: dict[str, Any]
    ) -> tuple[bool, str, dict[str, Any]]:
        """Authenticate using form data."""
        # Validate required fields
        required_fields = self.get_required_fields()
        for field in required_fields:
            if not form_data.get(field):
                return False, f"Missing required field: {field}", {}

        # Validate password confirmation
        if form_data.get("password") != form_data.get("confirm_password"):
            return False, "Passwords do not match", {}

        # Extract user data
        user_data = {
            "username": form_data.get("username"),
            "email": form_data.get("email"),
            "password": form_data.get("password"),
        }

        return True, "Form authentication successful", user_data

    def get_required_fields(self) -> list[str]:
        """Get required form fields."""
        return ["username", "email", "password", "confirm_password"]


class PlexOAuthStrategy(AuthenticationStrategy):
    """Strategy for Plex OAuth authentication."""

    def authenticate(
        self, servers: list[MediaServer], form_data: dict[str, Any]
    ) -> tuple[bool, str, dict[str, Any]]:
        """Authenticate using Plex OAuth."""
        # Check if we have OAuth token from session or form
        oauth_token = form_data.get("oauth_token") or session.get("plex_oauth_token")

        if not oauth_token:
            return False, "OAuth token required", {}

        # Validate OAuth token (simplified - in real implementation you'd validate with Plex)
        user_data = {
            "username": "plex_user",  # Would come from Plex API
            "email": "user@plex.tv",  # Would come from Plex API
            "plex_token": oauth_token,
        }

        return True, "Plex OAuth authentication successful", user_data

    def get_required_fields(self) -> list[str]:
        """OAuth doesn't require traditional form fields."""
        return []


class HybridStrategy(AuthenticationStrategy):
    """Strategy for mixed Plex OAuth + form-based authentication."""

    def __init__(self):
        super().__init__()
        self.plex_strategy = PlexOAuthStrategy()
        self.form_strategy = FormBasedStrategy()

    def authenticate(
        self, servers: list[MediaServer], form_data: dict[str, Any]
    ) -> tuple[bool, str, dict[str, Any]]:
        """Authenticate using hybrid approach."""
        # plex_servers = [s for s in servers if s.server_type == "plex"]
        other_servers = [s for s in servers if s.server_type != "plex"]

        # Check if we have Plex OAuth token
        plex_token = session.get("plex_oauth_token")

        if not plex_token:
            # Need to start with Plex OAuth
            return False, "Plex OAuth required", {"next_step": "plex_oauth"}

        # Have Plex token, now need password for other servers
        if not form_data.get("password"):
            return (
                False,
                "Password required for local servers",
                {"next_step": "collect_password"},
            )

        # Validate form data for local servers
        form_success, form_message, form_user_data = self.form_strategy.authenticate(
            other_servers, form_data
        )

        if form_success:
            # Combine Plex and form authentication data
            user_data = {**form_user_data, "plex_token": plex_token}
            return True, "Hybrid authentication successful", user_data

        return form_success, form_message, {}

    def get_required_fields(self) -> list[str]:
        """Required fields depend on authentication stage."""
        return ["username", "email", "password", "confirm_password"]


class StrategyFactory:
    """Factory for creating appropriate authentication strategies."""

    @staticmethod
    def create_strategy(servers: list[MediaServer]) -> AuthenticationStrategy:
        """Create appropriate strategy based on server types."""
        if not servers:
            return FormBasedStrategy()

        server_types = {server.server_type for server in servers}

        # Check for hybrid scenario
        has_plex = "plex" in server_types
        has_others = len(server_types) > 1 or not has_plex

        if has_plex and has_others:
            return HybridStrategy()

        if has_plex:
            return PlexOAuthStrategy()

        return FormBasedStrategy()
