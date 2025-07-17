"""
Simple result objects for invitation flow operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from flask import redirect, render_template, session

from app.models import MediaServer


class ProcessingStatus(Enum):
    """Processing result statuses."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    INVALID_INVITATION = "invalid_invitation"
    AUTHENTICATION_REQUIRED = "authentication_required"
    OAUTH_PENDING = "oauth_pending"


@dataclass
class ServerResult:
    """Result of processing a single server."""

    server: MediaServer
    success: bool
    message: str
    user_created: bool = False


@dataclass
class AuthResult:
    """Result of authentication processing."""

    success: bool
    message: str
    auth_data: dict[str, Any] | None = None


@dataclass
class InvitationResult:
    """Complete result of invitation processing."""

    status: ProcessingStatus
    message: str
    successful_servers: list[ServerResult]
    failed_servers: list[ServerResult]
    redirect_url: str | None = None
    template_data: dict[str, Any] | None = None
    session_data: dict[str, Any] | None = None

    def is_success(self) -> bool:
        """Check if the result indicates success."""
        return self.status == ProcessingStatus.SUCCESS

    def is_failure(self) -> bool:
        """Check if the result indicates failure."""
        return self.status == ProcessingStatus.FAILURE

    def is_partial_success(self) -> bool:
        """Check if the result indicates partial success."""
        return self.status == ProcessingStatus.PARTIAL_SUCCESS

    def has_successful_servers(self) -> bool:
        """Check if there are any successful servers."""
        return len(self.successful_servers) > 0

    def has_failed_servers(self) -> bool:
        """Check if there are any failed servers."""
        return len(self.failed_servers) > 0

    def get_error_messages(self) -> list[str]:
        """Get error messages from failed servers."""
        return [result.message for result in self.failed_servers]

    def get_success_messages(self) -> list[str]:
        """Get success messages from successful servers."""
        return [result.message for result in self.successful_servers]

    def to_flask_response(self):
        """Convert result to appropriate Flask response."""
        # Apply session data if provided
        if self.session_data:
            for key, value in self.session_data.items():
                session[key] = value

        # Handle redirects
        if self.redirect_url:
            return redirect(self.redirect_url)

        # Handle template rendering
        if self.template_data:
            template_name = self.template_data.get("template_name")
            if not template_name:
                # Fallback to invalid-invite.html
                return render_template("invalid-invite.html", error=self.message)

            # Create a copy without the template_name key
            context = {
                k: v for k, v in self.template_data.items() if k != "template_name"
            }
            return render_template(template_name, **context)

        # Default fallback
        return render_template("invalid-invite.html", error=self.message)
