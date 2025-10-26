"""
Simple invitation flow manager that integrates with existing routes.
"""

import logging
from typing import Any

from flask import session, url_for
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.models import Invitation, MediaServer, WizardBundleStep
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

            # Track bundle selection in session for downstream routes
            bundle_id = getattr(invitation, "wizard_bundle_id", None)
            if bundle_id:
                session["wizard_bundle_id"] = bundle_id
            else:
                session.pop("wizard_bundle_id", None)

            servers = self._get_invitation_servers(invitation)

            # Check for pre-invite wizard steps (Requirements 7.2-7.6)
            pre_steps_exist, bundle_redirect = self._check_pre_invite_steps_exist(
                invitation, servers
            )

            # Check if pre-wizard is complete (only if in request context)
            try:
                pre_wizard_complete = InviteCodeManager.is_pre_wizard_complete()
            except RuntimeError:
                # Not in request context - assume not complete
                pre_wizard_complete = False

            # If pre-invite steps exist and not completed, redirect to pre-wizard
            if pre_steps_exist and not pre_wizard_complete:
                redirect_url = (
                    bundle_redirect
                    if bundle_redirect is not None
                    else url_for("wizard.pre_wizard")
                )
                return InvitationResult(
                    status=ProcessingStatus.REDIRECT_REQUIRED,
                    message="Pre-wizard steps required",
                    successful_servers=[],
                    failed_servers=[],
                    redirect_url=redirect_url,
                    session_data={
                        "invitation_in_progress": True,
                        "wizard_bundle_id": bundle_id if bundle_id else None,
                    },
                )

            # Create appropriate workflow and show initial template
            # (Requirements 7.4, 7.5: Allow access if pre-wizard complete or no pre-invite steps)
            workflow = WorkflowFactory.create_workflow(servers)
            result = workflow.show_initial_form(invitation, servers)
            if bundle_id:
                session_data = result.session_data or {}
                session_data["wizard_bundle_id"] = bundle_id
                result.session_data = session_data
            else:
                session_data = result.session_data or {}
                session_data["wizard_bundle_id"] = None
                result.session_data = session_data
            return result

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

    def _check_pre_invite_steps_exist(
        self, invitation: Invitation, servers: list[MediaServer]
    ) -> tuple[bool, str | None]:
        """Check if any pre-invite wizard steps exist for the given servers.

        Args:
            invitation: Invitation object (used for bundle override)
            servers: List of media servers associated with the invitation

        Returns:
            Tuple:
                - bool indicating if pre-invite steps exist
                - optional redirect URL (used for bundle overrides)
        """
        bundle_id = getattr(invitation, "wizard_bundle_id", None)
        if bundle_id:
            bundle_steps = (
                WizardBundleStep.query.options(joinedload(WizardBundleStep.step))
                .filter(WizardBundleStep.bundle_id == bundle_id)
                .order_by(WizardBundleStep.position)
                .all()
            )
            has_pre_phase = any(
                assoc.step and assoc.step.category == "pre_invite"
                for assoc in bundle_steps
            )
            if has_pre_phase:
                return True, url_for("wizard.bundle_view", idx=0)
            return False, None

        if not servers:
            return False, None

        # Import here to avoid circular dependency
        from app.blueprints.wizard.routes import _settings, _steps

        # Check each server for pre-invite steps
        for server in servers:
            try:
                cfg = _settings()
                pre_steps = _steps(server.server_type, cfg, category="pre_invite")
                if pre_steps:
                    return True, None
            except Exception as e:
                self.logger.error(
                    f"Error checking pre-invite steps for {server.server_type}: {e}"
                )
                continue

        return False, None

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
