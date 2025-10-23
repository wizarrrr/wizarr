"""
Invite code management service for wizard pre/post-invite flow.

This service manages invite code persistence and validation across the invitation flow,
using Flask session for server-side storage to prevent client-side tampering.
"""

from flask import session

from app.extensions import db
from app.models import Invitation


class InviteCodeManager:
    """Manages invite code persistence and validation across the invitation flow."""

    STORAGE_KEY = "wizarr_invite_code"
    PRE_WIZARD_COMPLETE_KEY = "wizarr_pre_wizard_complete"

    @staticmethod
    def store_invite_code(code: str) -> None:
        """Store invite code in session for server-side validation.

        Args:
            code: Invitation code to store
        """
        previous_code = session.get(InviteCodeManager.STORAGE_KEY)

        # Reset completion flag when starting a new invitation flow.
        if previous_code != code:
            session.pop(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, None)

        session[InviteCodeManager.STORAGE_KEY] = code

    @staticmethod
    def get_invite_code() -> str | None:
        """Retrieve stored invite code from session.

        Returns:
            Invite code if stored, None otherwise
        """
        return session.get(InviteCodeManager.STORAGE_KEY)

    @staticmethod
    def validate_invite_code(code: str | None) -> tuple[bool, Invitation | None]:
        """Validate invite code and return invitation if valid.

        Checks:
        - Code exists in database
        - Invitation has not expired
        - Invitation has not been fully used (for limited invitations)

        Args:
            code: Invitation code to validate (can be None)

        Returns:
            Tuple of (is_valid, invitation_object)
            - is_valid: True if invitation is valid and can be used
            - invitation_object: Invitation model instance if valid, None otherwise
        """
        if not code:
            return False, None

        # Query invitation by code (case-insensitive)
        invitation = Invitation.query.filter(
            db.func.lower(Invitation.code) == code.lower()
        ).first()

        if not invitation:
            return False, None

        # Check if invitation is expired
        import datetime

        if invitation.expires:
            # Make database datetime timezone-aware (assumes UTC) for comparison
            expires_aware = invitation.expires.replace(tzinfo=datetime.UTC)
            now = datetime.datetime.now(datetime.UTC)
            if expires_aware <= now:
                return False, None

        # Check if invitation is fully used (limited invitations only)
        if not invitation.unlimited and invitation.used:
            return False, None

        return True, invitation

    @staticmethod
    def mark_pre_wizard_complete() -> None:
        """Mark pre-wizard steps as completed.

        Sets a flag in session indicating that the user has completed
        all pre-invite wizard steps and can proceed to the join page.
        """
        session[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] = True

    @staticmethod
    def is_pre_wizard_complete() -> bool:
        """Check if pre-wizard steps have been completed.

        Returns:
            True if pre-wizard completion flag is set, False otherwise
        """
        return session.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, False)

    @staticmethod
    def clear_invite_data() -> None:
        """Clear all invitation-related session data.

        Removes:
        - Stored invite code
        - Pre-wizard completion flag

        This should be called when:
        - User completes the entire invitation flow
        - Invitation becomes invalid or expires
        - User needs to restart the invitation process
        """
        session.pop(InviteCodeManager.STORAGE_KEY, None)
        session.pop(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, None)
