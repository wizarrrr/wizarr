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

        This method implements join page access control (Requirements 7.1-7.6):
        - Stores invite code in session
        - Checks for pre-invite wizard steps
        - Redirects to /pre-wizard if pre-invite steps exist and not completed
        - Allows access to join page if pre-wizard complete or no pre-invite steps
        """
        try:
            # Store invite code in session (Requirement 7.1)
            # Only store if we're in a request context
            import contextlib

            from app.services.invite_code_manager import InviteCodeManager

            with contextlib.suppress(RuntimeError):
                # Not in request context (e.g., during testing without app context)
                InviteCodeManager.store_invite_code(code)

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

            if not invitation:
                return InvitationResult(
                    status=ProcessingStatus.INVALID_INVITATION,
                    message="Invitation not found",
                    successful_servers=[],
                    failed_servers=[],
                    template_data={
                        "template_name": "invalid-invite.html",
                        "error": "Invitation not found",
                    },
                )

            servers = self._get_invitation_servers(invitation)

            # Check for pre-invite wizard steps (Requirements 7.2-7.6)
            pre_steps_exist = self._check_pre_invite_steps_exist(servers)

            # Check if pre-wizard is complete (only if in request context)
            try:
                pre_wizard_complete = InviteCodeManager.is_pre_wizard_complete()
            except RuntimeError:
                # Not in request context - assume not complete
                pre_wizard_complete = False

            # If pre-invite steps exist and not completed, redirect to pre-wizard
            if pre_steps_exist and not pre_wizard_complete:
                return InvitationResult(
                    status=ProcessingStatus.REDIRECT_REQUIRED,
                    message="Pre-wizard steps required",
                    successful_servers=[],
                    failed_servers=[],
                    redirect_url="/wizard/pre-wizard",
                    session_data={"invitation_in_progress": True},
                )

            # Create appropriate workflow and show initial template
            # (Requirements 7.4, 7.5: Allow access if pre-wizard complete or no pre-invite steps)
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

            if not invitation:
                return self._create_error_result("Invitation not found")

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

    def _check_pre_invite_steps_exist(self, servers: list[MediaServer]) -> bool:
        """Check if any pre-invite wizard steps exist for the given servers.

        Args:
            servers: List of media servers associated with the invitation

        Returns:
            True if pre-invite steps exist for any server, False otherwise
        """
        if not servers:
            return False

        # Import here to avoid circular dependency
        from app.blueprints.wizard.routes import _settings, _steps

        # Check each server for pre-invite steps
        for server in servers:
            try:
                cfg = _settings()
                pre_steps = _steps(server.server_type, cfg, category="pre_invite")
                if pre_steps:
                    return True
            except Exception as e:
                self.logger.error(
                    f"Error checking pre-invite steps for {server.server_type}: {e}"
                )
                continue

        return False

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
