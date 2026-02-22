"""
Simple workflow implementations for invitation flows.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from flask import session, url_for

from app.models import Invitation, MediaServer
from app.services.media.service import get_client_for_media_server
from app.services.ombi_client import invite_user_to_connections

from .results import InvitationResult, ProcessingStatus, ServerResult
from .strategies import StrategyFactory


def _get_server_colors(server_type: str | None) -> dict[str, str]:
    """Get color scheme for a specific server type.

    Args:
        server_type: Server type string (e.g., 'plex', 'jellyfin', 'emby', 'audiobookshelf')

    Returns:
        Dictionary containing:
        - gradient_start: Starting color for gradient
        - gradient_end: Ending color for gradient
        - shadow_color: RGBA color for box shadow (with 0.3 alpha)

    Note:
        Default colors (Plex red) are used for unknown server types and as fallback.
    """
    color_schemes = {
        "plex": {
            "gradient_start": "#fe4155",
            "gradient_end": "#fe4155",
            "shadow_color": "rgba(254, 65, 85, 0.3)",
        },
        "jellyfin": {
            "gradient_start": "#AA5CC3",
            "gradient_end": "#00A4DC",
            "shadow_color": "rgba(0, 164, 220, 0.3)",
        },
        "audiobookshelf": {
            "gradient_start": "#DDBC82",
            "gradient_end": "#8D6229",
            "shadow_color": "rgba(141, 98, 41, 0.3)",
        },
        "emby": {
            "gradient_start": "#52b64b",
            "gradient_end": "#52b64b",
            "shadow_color": "rgba(82, 182, 75, 0.3)",
        },
    }

    # Return server-specific colors or default to Plex colors
    return color_schemes.get(
        server_type,
        color_schemes["plex"],
    )


class InvitationWorkflow(ABC):
    """Base class for invitation workflows."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def show_initial_form(
        self, invitation: Invitation, servers: list[MediaServer]
    ) -> InvitationResult:
        """Show the initial form for this workflow type."""

    @abstractmethod
    def process_submission(
        self,
        invitation: Invitation,
        servers: list[MediaServer],
        form_data: dict[str, Any],
    ) -> InvitationResult:
        """Process form submission for this workflow type."""

    def _process_servers(
        self,
        servers: list[MediaServer],
        form_data: dict[str, Any],
        invitation_code: str,
    ) -> tuple[list[ServerResult], list[ServerResult]]:
        """Process account creation for multiple servers."""
        successful = []
        failed = []

        for server in servers:
            try:
                client = get_client_for_media_server(server)
                ok, msg = client.join(
                    username=form_data.get("username", ""),
                    password=form_data.get("password", ""),
                    confirm=form_data.get("confirm_password", ""),
                    email=form_data.get("email", ""),
                    code=invitation_code,
                    is_ldap_user=form_data.get("is_ldap_user", False),
                )

                result = ServerResult(
                    server=server, success=ok, message=msg, user_created=ok
                )

                if ok:
                    successful.append(result)

                    # Mark invitation as used for this server
                    from app.models import Invitation
                    from app.services.invites import mark_server_used

                    invitation = Invitation.query.filter_by(
                        code=invitation_code
                    ).first()
                    if invitation:
                        # Find the user that was created for this server
                        # Flush and commit to ensure we can see the newly created user
                        from app.extensions import db
                        from app.models import User

                        db.session.flush()
                        db.session.commit()

                        user = User.query.filter_by(
                            code=invitation_code, server_id=server.id
                        ).first()

                        # If user not found, log debug info
                        if not user:
                            import logging

                            all_users_for_server = User.query.filter_by(
                                server_id=server.id
                            ).all()
                            all_users_with_code = User.query.filter_by(
                                code=invitation_code
                            ).all()
                            logging.error(
                                f"User lookup failed for code={invitation_code}, server_id={server.id}. "
                                f"Server has {len(all_users_for_server)} users, "
                                f"code has {len(all_users_with_code)} users globally."
                            )
                        # Only set used_by for unlimited invites if not already set
                        # For limited invites, used_by should track the single user
                        if user and (
                            not invitation.unlimited or not invitation.used_by
                        ):
                            invitation.used_by = user  # type: ignore[assignment]
                        mark_server_used(invitation, server.id, user)

                    # Invite user to connected external services (Ombi/Overseerr)
                    try:
                        connection_results = invite_user_to_connections(
                            username=form_data.get("username", ""),
                            email=form_data.get("email", ""),
                            server_id=server.id,
                            password=form_data.get("password", ""),
                        )

                        # Log connection results for debugging
                        for conn_result in connection_results:
                            if conn_result["status"] == "success":
                                self.logger.info(
                                    f"User {form_data.get('username')} invited to {conn_result['connection_name']}"
                                )
                            elif conn_result["status"] == "error":
                                self.logger.warning(
                                    f"Failed to invite user to {conn_result['connection_name']}: {conn_result['message']}"
                                )
                    except Exception as e:
                        self.logger.error(
                            f"Error inviting user to connections for server {server.name}: {e}"
                        )
                else:
                    failed.append(result)

            except Exception as e:
                self.logger.error(f"Failed to process server {server.name}: {e}")
                failed.append(
                    ServerResult(
                        server=server,
                        success=False,
                        message=f"Error: {e!s}",
                        user_created=False,
                    )
                )

        return successful, failed

    def _create_success_result(
        self,
        invitation: Invitation,
        successful: list[ServerResult],
        failed: list[ServerResult],
    ) -> InvitationResult:
        """Create success result with wizard redirect."""
        invitation_code = invitation.code
        session["wizard_access"] = invitation_code
        bundle_id = getattr(invitation, "wizard_bundle_id", None)
        if bundle_id:
            session["wizard_bundle_id"] = bundle_id
        else:
            session.pop("wizard_bundle_id", None)

        if not failed:
            status = ProcessingStatus.SUCCESS
            message = "Accounts created successfully on all servers"
        else:
            status = ProcessingStatus.PARTIAL_SUCCESS
            message = f"Accounts created on {len(successful)} of {len(successful) + len(failed)} servers"

        redirect_url = "/wizard/"
        if bundle_id:
            redirect_url = url_for("wizard.bundle_view", idx=0)

        return InvitationResult(
            status=status,
            message=message,
            successful_servers=successful,
            failed_servers=failed,
            redirect_url=redirect_url,
            session_data={
                "wizard_access": invitation_code,
                "invitation_in_progress": True,
                "wizard_bundle_id": bundle_id,
            },
        )


class FormBasedWorkflow(InvitationWorkflow):
    """Workflow for form-based authentication servers."""

    def show_initial_form(
        self, invitation: Invitation, servers: list[MediaServer]
    ) -> InvitationResult:
        """Show form-based authentication form."""
        from app.forms.join import JoinForm
        from app.services.server_name_resolver import resolve_invitation_server_name

        form = JoinForm()
        form.code.data = invitation.code

        # Determine primary server type for UI
        primary_server = servers[0] if servers else None
        server_type = primary_server.server_type if primary_server else "jellyfin"

        # Resolve the server name to display
        server_name = resolve_invitation_server_name(servers)

        # Get server-specific color scheme for theming
        colors = _get_server_colors(server_type)

        return InvitationResult(
            status=ProcessingStatus.AUTHENTICATION_REQUIRED,
            message="Authentication required",
            successful_servers=[],
            failed_servers=[],
            template_data={
                "template_name": "welcome-jellyfin.html",
                "form": form,
                "server_type": server_type,
                "server_name": server_name,
                "servers": servers,
                "gradient_start": colors["gradient_start"],
                "gradient_end": colors["gradient_end"],
                "shadow_color": colors["shadow_color"],
            },
            session_data={"invitation_in_progress": True},
        )

    def process_submission(
        self,
        invitation: Invitation,
        servers: list[MediaServer],
        form_data: dict[str, Any],
    ) -> InvitationResult:
        """Process form submission."""
        # Authenticate
        strategy = StrategyFactory.create_strategy(servers)
        auth_success, auth_message, _user_data = strategy.authenticate(
            servers, form_data
        )

        if not auth_success:
            return self._create_auth_error_result(invitation, servers, auth_message)

        # Create LDAP user if configured
        from app.services.ldap.invitation_ldap import InvitationLDAPHandler

        ldap_handler = InvitationLDAPHandler(invitation)

        if ldap_handler.should_create_ldap_user():
            ldap_success, ldap_result = ldap_handler.create_ldap_user(
                username=form_data.get("username", ""),
                email=form_data.get("email", ""),
                password=form_data.get("password", ""),
            )

            if not ldap_success:
                return self._create_auth_error_result(
                    invitation, servers, f"Failed to create LDAP user: {ldap_result}"
                )

            # Mark that this is an LDAP user
            form_data["is_ldap_user"] = True

        # Process servers
        successful, failed = self._process_servers(servers, form_data, invitation.code)

        if successful:
            return self._create_success_result(invitation, successful, failed)
        return self._create_server_error_result(invitation, servers, failed)

    def _create_auth_error_result(
        self, invitation: Invitation, servers: list[MediaServer], error_message: str
    ) -> InvitationResult:
        """Create result for authentication errors."""
        from app.forms.join import JoinForm
        from app.services.server_name_resolver import resolve_invitation_server_name

        form = JoinForm()
        form.code.data = invitation.code

        primary_server = servers[0] if servers else None
        server_type = primary_server.server_type if primary_server else "jellyfin"

        # Resolve the server name to display
        server_name = resolve_invitation_server_name(servers)

        return InvitationResult(
            status=ProcessingStatus.FAILURE,
            message=error_message,
            successful_servers=[],
            failed_servers=[],
            template_data={
                "template_name": "welcome-jellyfin.html",
                "form": form,
                "server_type": server_type,
                "server_name": server_name,
                "servers": servers,
                "error": error_message,
            },
            session_data={"invitation_in_progress": True},
        )

    def _create_server_error_result(
        self,
        invitation: Invitation,
        servers: list[MediaServer],
        failed: list[ServerResult],
    ) -> InvitationResult:
        """Create result for server failures."""
        from app.forms.join import JoinForm
        from app.services.server_name_resolver import resolve_invitation_server_name

        form = JoinForm()
        form.code.data = invitation.code

        primary_server = servers[0] if servers else None
        server_type = primary_server.server_type if primary_server else "jellyfin"

        # Resolve the server name to display
        server_name = resolve_invitation_server_name(servers)

        error_messages = [
            f"{result.server.name}: {result.message}" for result in failed
        ]
        error_text = "; ".join(error_messages)

        return InvitationResult(
            status=ProcessingStatus.FAILURE,
            message=error_text,
            successful_servers=[],
            failed_servers=failed,
            template_data={
                "template_name": "welcome-jellyfin.html",
                "form": form,
                "server_type": server_type,
                "server_name": server_name,
                "servers": servers,
                "error": error_text,
            },
            session_data={"invitation_in_progress": True},
        )


class PlexOAuthWorkflow(InvitationWorkflow):
    """Workflow for Plex OAuth authentication."""

    def show_initial_form(
        self, invitation: Invitation, servers: list[MediaServer]
    ) -> InvitationResult:
        """Show Plex OAuth form."""
        from app.services.server_name_resolver import resolve_invitation_server_name

        # Resolve the server name to display
        server_name = resolve_invitation_server_name(servers)

        # Get server-specific color scheme for theming (always Plex for this workflow)
        colors = _get_server_colors("plex")

        return InvitationResult(
            status=ProcessingStatus.OAUTH_PENDING,
            message="Plex OAuth authentication required",
            successful_servers=[],
            failed_servers=[],
            template_data={
                "template_name": "user-plex-login.html",
                "code": invitation.code,
                "oauth_url": f"/oauth/plex?code={invitation.code}",
                "server_name": server_name,
                "gradient_start": colors["gradient_start"],
                "gradient_end": colors["gradient_end"],
                "shadow_color": colors["shadow_color"],
            },
            session_data={"invitation_in_progress": True},
        )

    def process_submission(
        self,
        invitation: Invitation,
        servers: list[MediaServer],
        form_data: dict[str, Any],
    ) -> InvitationResult:
        """Process OAuth submission."""
        # Check if we have OAuth token
        oauth_token = form_data.get("oauth_token") or session.get("plex_oauth_token")

        if not oauth_token:
            return self.show_initial_form(invitation, servers)

        # Store token in session for server processing
        session["plex_oauth_token"] = oauth_token

        # Process servers
        successful, failed = self._process_servers(servers, form_data, invitation.code)

        if successful:
            return self._create_success_result(invitation, successful, failed)
        return self._create_oauth_error_result(
            invitation, "Failed to create Plex account"
        )

    def _create_oauth_error_result(
        self, invitation: Invitation, error_message: str
    ) -> InvitationResult:
        """Create result for OAuth errors."""
        from typing import Any, cast

        from app.services.server_name_resolver import resolve_invitation_server_name

        # Get servers from invitation and resolve the server name
        servers = []
        if hasattr(invitation, "servers") and invitation.servers:
            try:
                servers_iter = cast(Any, invitation.servers)
                servers = list(servers_iter)
            except (TypeError, AttributeError):
                servers = []
        server_name = resolve_invitation_server_name(servers)

        return InvitationResult(
            status=ProcessingStatus.FAILURE,
            message=error_message,
            successful_servers=[],
            failed_servers=[],
            template_data={
                "template_name": "user-plex-login.html",
                "code": invitation.code,
                "error": error_message,
                "server_name": server_name,
            },
            session_data={"invitation_in_progress": True},
        )


class MixedWorkflow(InvitationWorkflow):
    """Workflow for mixed Plex + other server authentication."""

    def show_initial_form(
        self, invitation: Invitation, servers: list[MediaServer]
    ) -> InvitationResult:
        """Show initial form based on authentication state."""
        plex_token = session.get("plex_oauth_token")
        other_servers = [s for s in servers if s.server_type != "plex"]

        if not plex_token:
            # Start with Plex OAuth
            from app.services.server_name_resolver import resolve_invitation_server_name

            # Resolve the server name to display
            server_name = resolve_invitation_server_name(servers)

            # Get server-specific color scheme for theming (Plex for mixed workflow)
            colors = _get_server_colors("plex")

            return InvitationResult(
                status=ProcessingStatus.OAUTH_PENDING,
                message="Plex OAuth authentication required",
                successful_servers=[],
                failed_servers=[],
                template_data={
                    "template_name": "user-plex-login.html",
                    "code": invitation.code,
                    "oauth_url": f"/oauth/plex?code={invitation.code}",
                    "server_name": server_name,
                    "gradient_start": colors["gradient_start"],
                    "gradient_end": colors["gradient_end"],
                    "shadow_color": colors["shadow_color"],
                },
                session_data={"invitation_in_progress": True},
            )

        if other_servers:
            # Show password form for local servers
            # Use first local server's colors
            local_server_type = other_servers[0].server_type if other_servers else None
            colors = _get_server_colors(local_server_type)

            return InvitationResult(
                status=ProcessingStatus.AUTHENTICATION_REQUIRED,
                message="Password required for local servers",
                successful_servers=[],
                failed_servers=[],
                template_data={
                    "template_name": "hybrid-password-form.html",
                    "code": invitation.code,
                    "plex_authenticated": True,
                    "plex_token": plex_token,
                    "local_servers": other_servers,
                    "gradient_start": colors["gradient_start"],
                    "gradient_end": colors["gradient_end"],
                    "shadow_color": colors["shadow_color"],
                },
                session_data={"invitation_in_progress": True},
            )

        # Only Plex servers, proceed with processing
        return self.process_submission(invitation, servers, {})

    def process_submission(
        self,
        invitation: Invitation,
        servers: list[MediaServer],
        form_data: dict[str, Any],
    ) -> InvitationResult:
        """Process mixed submission."""
        plex_servers = [s for s in servers if s.server_type == "plex"]
        other_servers = [s for s in servers if s.server_type != "plex"]

        # Check authentication state
        plex_token = session.get("plex_oauth_token")

        if not plex_token:
            # Need Plex OAuth first
            return self.show_initial_form(invitation, servers)

        if other_servers and not form_data.get("password"):
            # Need password for local servers
            return self.show_initial_form(invitation, servers)

        # Process all servers
        all_successful = []
        all_failed = []

        # Process Plex servers with OAuth token
        if plex_servers:
            plex_data = dict(form_data)
            plex_data["oauth_token"] = plex_token

            plex_successful, plex_failed = self._process_servers(
                plex_servers, plex_data, invitation.code
            )
            all_successful.extend(plex_successful)
            all_failed.extend(plex_failed)

        # Process other servers with form data
        if other_servers:
            other_successful, other_failed = self._process_servers(
                other_servers, form_data, invitation.code
            )
            all_successful.extend(other_successful)
            all_failed.extend(other_failed)

        if all_successful:
            return self._create_success_result(invitation, all_successful, all_failed)
        return self._create_mixed_error_result(
            invitation, "Failed to create accounts on any server"
        )

    def _create_mixed_error_result(
        self, _invitation: Invitation, error_message: str
    ) -> InvitationResult:
        """Create result for mixed workflow errors."""
        return InvitationResult(
            status=ProcessingStatus.FAILURE,
            message=error_message,
            successful_servers=[],
            failed_servers=[],
            template_data={
                "template_name": "invalid-invite.html",
                "error": error_message,
            },
        )


class WorkflowFactory:
    """Factory for creating appropriate workflows."""

    @staticmethod
    def create_workflow(servers: list[MediaServer]) -> InvitationWorkflow:
        """Create appropriate workflow based on server types."""
        if not servers:
            return FormBasedWorkflow()

        server_types = {server.server_type for server in servers}

        # Check for mixed scenario
        has_plex = "plex" in server_types
        has_others = len(server_types) > 1 or not has_plex

        if has_plex and has_others:
            return MixedWorkflow()

        if has_plex:
            return PlexOAuthWorkflow()

        return FormBasedWorkflow()
