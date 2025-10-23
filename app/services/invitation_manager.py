"""Centralized invitation management service.

This module provides common functionality for processing invitations across
all media server types, eliminating code duplication in blueprints.
"""

from flask import session

from app.extensions import db
from app.models import Identity, Invitation, MediaServer, User
from app.services.media.service import get_client_for_media_server


class InvitationManager:
    """Handles invitation processing across multiple media servers."""

    @staticmethod
    def ensure_invitation_identity(
        code: str, username: str, email: str
    ) -> Identity | None:
        """Ensure there's a shared Identity for users created from this invitation.

        This allows users created from the same invitation code to be pre-linked,
        but only for limited invitations OR unlimited invitations with the same email.

        Args:
            code: Invitation code
            username: Username from the invitation form
            email: Email from the invitation form (may be invalid)

        Returns:
            Identity: Shared identity for this invitation, or None if no identity should be shared
        """
        # Get the invitation to check its type
        invitation = Invitation.query.filter_by(code=code).first()
        if not invitation:
            return None

        if invitation.unlimited:
            # For UNLIMITED invitations: only link users with the same EMAIL (same person)
            if not email or "@" not in email:
                return None  # No valid email = no identity linking

            # Check if we already have a user with this invitation code AND email
            existing_user = User.query.filter_by(code=code, email=email).first()
            if existing_user and existing_user.identity:
                # Use existing identity for the same email
                return existing_user.identity

            # Check if there are any users with the same code but different emails
            other_users = (
                User.query.filter_by(code=code).filter(User.email != email).first()
            )
            if other_users:
                # Other users exist with different emails - don't link
                return None

            # Create new identity only if this is the first user or same email
            identity = Identity(
                primary_email=email,
                primary_username=username,
            )
            db.session.add(identity)
            db.session.flush()
            return identity

        # For LIMITED invitations: always link users with the same code (multi-server for same person)
        existing_user = User.query.filter_by(code=code).first()

        if existing_user and existing_user.identity:
            # Use existing identity from previous user creation
            return existing_user.identity

        # Create new identity for this invitation
        identity = Identity(
            primary_email=email if email and "@" in email else None,
            primary_username=username,
        )
        db.session.add(identity)
        db.session.flush()  # Get the ID immediately

        # Link existing users for this code (limited invitations only)
        existing_users = User.query.filter_by(code=code).all()
        for user in existing_users:
            if not user.identity_id:
                user.identity_id = identity.id

        return identity

    @staticmethod
    def process_invitation(
        code: str, username: str, password: str, confirm_password: str, email: str
    ) -> tuple[bool, str | None, list[str]]:
        """Process an invitation across all associated media servers.

        Args:
            code: Invitation code
            username: Username for new account
            password: Password for new account
            confirm_password: Password confirmation
            email: Email address for new account

        Returns:
            tuple: (success: bool, redirect_code: str|None, errors: List[str])
                - success: True if at least one server succeeded
                - redirect_code: Code to set in session if successful
                - errors: List of error messages from failed servers
        """
        # Get invitation
        inv = Invitation.query.filter_by(code=code).first()
        if not inv:
            return False, None, ["Invalid invitation code"]

        # Determine servers to process
        servers_to_process = (
            inv.servers
            if inv.servers
            else [inv.server]
            if inv.server
            else [MediaServer.query.first()]
        )

        # Pre-create shared identity for multi-server invitations
        # Only create if the invitation type supports it (limited invites always, unlimited only with same email)
        if len(servers_to_process) > 1:
            InvitationManager.ensure_invitation_identity(code, username, email)

        errors = []
        success_count = 0

        for server in servers_to_process:
            if not server:
                continue

            try:
                client = get_client_for_media_server(server)
                ok, msg = client.join(
                    username=username,
                    password=password,
                    confirm=confirm_password,
                    email=email,
                    code=code,
                )

                if ok:
                    success_count += 1

                    # Mark invitation as used for this server
                    from app.services.invites import mark_server_used

                    invitation = Invitation.query.filter_by(code=code).first()
                    if invitation:
                        # Find the user that was created for this server
                        # Flush and commit to ensure we can see the newly created user
                        db.session.flush()
                        db.session.commit()

                        user = User.query.filter_by(
                            code=code, server_id=server.id
                        ).first()

                        # If user not found, log debug info
                        if not user:
                            import logging

                            all_users_for_server = User.query.filter_by(
                                server_id=server.id
                            ).all()
                            all_users_with_code = User.query.filter_by(code=code).all()
                            logging.error(
                                f"User lookup failed for code={code}, server_id={server.id}. "
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
                else:
                    errors.append(f"{server.name} ({server.server_type}): {msg}")

            except Exception as e:
                errors.append(f"{server.name} ({server.server_type}): {e!s}")

        # Return results
        if success_count > 0:
            return True, code, errors
        return False, None, errors or ["Failed to create accounts on any server"]

    @staticmethod
    def handle_successful_join(code: str) -> str:
        """Handle successful invitation join by setting session and redirecting.

        Args:
            code: Invitation code to store in session

        Returns:
            str: Redirect URL
        """
        session["wizard_access"] = code
        return "/wizard/"


class LibraryScanner:
    """Handles library scanning across media server types."""

    @staticmethod
    def scan_with_credentials(
        server_type: str, url: str, api_key: str
    ) -> tuple[bool, dict]:
        """Scan libraries using provided credentials.

        Args:
            server_type: Type of media server
            url: Server URL
            api_key: API key/token

        Returns:
            tuple: (success: bool, libraries: dict)
        """
        try:
            # Import here to avoid circular imports
            from app.services.media.client_base import CLIENTS

            if server_type not in CLIENTS:
                return False, {}

            client_class = CLIENTS[server_type]
            # Create temporary client with override credentials
            client = client_class()
            client.url = url
            client.token = api_key

            libraries = client.scan_libraries(url=url, token=api_key)
            return True, libraries

        except Exception:
            return False, {}

    @staticmethod
    def scan_with_saved_credentials(server_type: str) -> tuple[bool, dict]:
        """Scan libraries using saved server credentials.

        Args:
            server_type: Type of media server

        Returns:
            tuple: (success: bool, libraries: dict)
        """
        try:
            from app.services.media.client_base import CLIENTS

            if server_type not in CLIENTS:
                return False, {}

            client_class = CLIENTS[server_type]
            client = client_class()

            libraries = client.scan_libraries()
            return True, libraries

        except Exception:
            return False, {}
