"""
Simple invitation flow manager that integrates with existing routes.
"""

import logging
from typing import Any

from sqlalchemy import func

from app.models import Invitation, MediaServer
from app.services.invites import is_invite_valid

from .results import InvitationResult, ProcessingStatus
from .workflows import WorkflowFactory


class InvitationFlowManager:
    """
    Simple manager that can be used as a drop-in replacement for existing invitation processing.

    Usage:
        manager = InvitationFlowManager()
        result = manager.process_invitation_display(code)
        return result.to_flask_response()
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_invitation_display(self, code: str) -> InvitationResult:
        """
        Process invitation display (GET /j/<code>).

        Drop-in replacement for existing invitation display logic.
        """
        try:
            # Validate invitation (reuse existing logic)
            valid, message = is_invite_valid(code)
            if not valid:
                return InvitationResult(
                    status=ProcessingStatus.INVALID_INVITATION,
                    message=message,
                    successful_servers=[],
                    failed_servers=[],
                    template_data={
                        "template_name": "invalid-invite.html",
                        "error": message,
                    },
                )

            # Get invitation and servers
            invitation = Invitation.query.filter(
                func.lower(Invitation.code) == code.lower()
            ).first()

            servers = self._get_invitation_servers(invitation)

            # Create appropriate workflow and show initial template
            workflow = WorkflowFactory.create_workflow(servers)
            return workflow.show_initial_form(invitation, servers)

        except Exception as e:
            self.logger.error(f"Error displaying invitation {code}: {e}")
            return self._create_error_result(str(e))

    def process_invitation_submission(
        self, form_data: dict[str, Any]
    ) -> InvitationResult:
        """
        Process invitation form submission (POST).

        Drop-in replacement for existing invitation processing logic.
        """
        try:
            code = form_data.get("code")
            if not code:
                return self._create_error_result("Missing invitation code")

            # Validate invitation
            valid, message = is_invite_valid(code)
            if not valid:
                return self._create_error_result(message)

            # Get invitation and servers
            invitation = Invitation.query.filter(
                func.lower(Invitation.code) == code.lower()
            ).first()

            servers = self._get_invitation_servers(invitation)

            # Process with appropriate workflow
            workflow = WorkflowFactory.create_workflow(servers)
            return workflow.process_submission(invitation, servers, form_data)

        except Exception as e:
            self.logger.error(f"Error processing invitation submission: {e}")
            return self._create_error_result(str(e))

    def _get_invitation_servers(self, invitation: Invitation) -> list[MediaServer]:
        """Get servers associated with invitation (same logic as existing system)."""
        servers = []

        # Check new many-to-many relationship first
        if hasattr(invitation, "servers") and invitation.servers:
            try:
                # Cast to Any to work around type checking issues with SQLAlchemy relationships
                from typing import Any, cast

                servers_iter = cast(Any, invitation.servers)
                servers = list(servers_iter)
            except (TypeError, AttributeError):
                # Fallback if servers is not iterable
                servers = []

        # Fallback to legacy single server relationship
        if not servers and hasattr(invitation, "server") and invitation.server:
            servers = [invitation.server]

        # Final fallback to first available server
        if not servers:
            default_server = MediaServer.query.first()
            if default_server:
                servers = [default_server]

        # Ensure Plex servers are first for mixed workflows
        plex_servers = [s for s in servers if s.server_type == "plex"]
        other_servers = [s for s in servers if s.server_type != "plex"]

        return plex_servers + other_servers

    def _create_error_result(self, message: str) -> InvitationResult:
        """Create generic error result."""
        return InvitationResult(
            status=ProcessingStatus.FAILURE,
            message=message,
            successful_servers=[],
            failed_servers=[],
            template_data={"template_name": "invalid-invite.html", "error": message},
            session_data={"invitation_in_progress": True},
        )
