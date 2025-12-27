import logging
from typing import TYPE_CHECKING

from app.models import LDAPConfiguration

from .client import LDAPClient

if TYPE_CHECKING:
    from app.models import Invitation

logger = logging.getLogger(__name__)


class InvitationLDAPHandler:
    def __init__(self, invitation: "Invitation"):
        self.invitation = invitation
        self.config = LDAPConfiguration.query.first()

    def should_create_ldap_user(self) -> bool:
        if not self.config or not self.config.enabled:
            return False

        # Check the invitation's create_ldap_user flag (defaults to True in UI)
        # If None or True, create the user; only skip if explicitly False
        return self.invitation.create_ldap_user is not False

    def create_ldap_user(
        self,
        username: str,
        email: str,
        password: str,
    ) -> tuple[bool, str]:
        if not self.should_create_ldap_user():
            return False, "LDAP user creation not enabled"

        try:
            client = LDAPClient(self.config)

            # Create the LDAP user
            success, result = client.create_user(
                username=username,
                email=email,
                password=password,
            )

            if not success:
                logger.error("Failed to create LDAP user: %s", result)
                return False, result

            user_dn = result

            logger.info(
                "Successfully created LDAP user %s for invitation %s",
                user_dn,
                self.invitation.code,
            )
            return True, user_dn

        except Exception as e:
            logger.exception("Unexpected error creating LDAP user for invitation")
            return False, f"Unexpected error: {e}"
