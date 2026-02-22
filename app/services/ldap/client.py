import logging
from typing import Any

from ldap3 import ALL, BASE, MODIFY_REPLACE, SUBTREE, Connection, Server
from ldap3.core.exceptions import (
    LDAPBindError,
    LDAPException,
    LDAPInvalidDnError,
    LDAPSocketOpenError,
)
from ldap3.utils.conv import escape_filter_chars

from app.models import LDAPConfiguration

from .encryption import decrypt_credential

logger = logging.getLogger(__name__)


class LDAPClient:
    def __init__(self, config: LDAPConfiguration):
        self.config = config
        self._server = self._create_server()

    def _create_server(self) -> Server:
        return Server(
            self.config.server_url,
            use_ssl=self.config.use_tls,
            get_info=ALL,
        )

    def test_connection(self) -> tuple[bool, str]:
        if not self.config.service_account_dn:
            return False, "Service account DN not configured"

        try:
            password = decrypt_credential(
                self.config.service_account_password_encrypted or ""
            )
            if not password:
                return False, "Service account password not configured"

            conn = Connection(
                self._server,
                user=self.config.service_account_dn,
                password=password,
                auto_bind=True,
            )
            conn.unbind()
            return True, "Connection successful"

        except LDAPSocketOpenError as e:
            logger.warning("LDAP connection failed: %s", e)
            return False, f"Cannot connect to LDAP server: {e}"
        except LDAPBindError as e:
            logger.warning("LDAP bind failed: %s", e)
            return False, f"Authentication failed: {e}"
        except LDAPException as e:
            logger.exception("LDAP test connection error")
            return False, f"LDAP error: {e}"
        except Exception as e:
            logger.exception("Unexpected error testing LDAP connection")
            return False, f"Unexpected error: {e}"

    def authenticate_user(self, username: str, password: str) -> tuple[bool, dict]:
        try:
            # Search for user DN first
            user_dn = self._find_user_dn(username)
            if not user_dn:
                return False, {}

            # Attempt bind with user credentials
            conn = Connection(
                self._server,
                user=user_dn,
                password=password,
                auto_bind=True,
            )

            # Fetch user attributes
            attrs = self._fetch_user_attributes(conn, user_dn)
            conn.unbind()

            return True, attrs

        except LDAPBindError:
            logger.info("LDAP authentication failed for user: %s", username)
            return False, {}
        except LDAPException:
            logger.exception("LDAP authentication error for user: %s", username)
            return False, {}

    def _find_user_dn(self, username: str) -> str | None:
        try:
            conn = self._service_connection()
            if not conn:
                return None

            # Escape username to prevent LDAP injection
            escaped_username = escape_filter_chars(username)
            search_filter = self.config.user_search_filter.replace(
                "{username}", escaped_username
            )

            conn.search(
                search_base=self.config.user_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=[self.config.username_attribute],
            )

            if conn.entries:
                user_dn = str(conn.entries[0].entry_dn)
                conn.unbind()
                return user_dn

            conn.unbind()
            return None

        except LDAPException as e:
            logger.exception("Error searching for user DN", exc_info=e)
            return None

    def _fetch_user_attributes(self, conn: Connection, user_dn: str) -> dict:
        attributes = [
            self.config.username_attribute,
            self.config.email_attribute,
        ]

        conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            search_scope=SUBTREE,
            attributes=attributes,
        )

        if not conn.entries:
            return {"dn": user_dn}

        entry = conn.entries[0]
        attrs: dict[str, Any] = {"dn": user_dn}

        # Extract attributes safely
        for attr in attributes:
            if hasattr(entry, attr):
                value = getattr(entry, attr).value
                attrs[attr] = str(value) if value else None

        return attrs

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
    ) -> tuple[bool, str]:
        try:
            conn = self._service_connection()
            if not conn:
                return False, "Cannot connect to LDAP server"

            # Construct user DN
            user_dn = f"{self.config.username_attribute}={username},{self.config.user_base_dn}"

            # Check if user already exists
            conn.search(
                search_base=user_dn,
                search_filter="(objectClass=*)",
                search_scope=BASE,
            )

            user_exists = bool(conn.entries)

            if user_exists:
                # Update existing user
                logger.info("User %s already exists, updating attributes", user_dn)

                changes = {
                    self.config.email_attribute: [(MODIFY_REPLACE, [email])],
                }

                success = conn.modify(user_dn, changes)

                if not success:
                    conn.unbind()
                    return False, f"Failed to update user attributes: {conn.result}"

                # Update password using LDAP Password Modify Extended Operation (RFC 3062)
                # Required for LLDAP - service account must be in lldap_password_manager group
                try:
                    password_success = conn.extend.standard.modify_password(
                        user_dn, None, password
                    )
                    if password_success:
                        logger.info("Updated LDAP user password: %s", user_dn)
                    else:
                        logger.warning(
                            "Failed to update password for %s. Ensure service account is in lldap_password_manager group. Result: %s",
                            user_dn,
                            conn.result,
                        )
                except Exception as e:
                    logger.warning("Password update failed for %s: %s", user_dn, e)

                conn.unbind()
                return True, user_dn

            # Create new user without password (LLDAP doesn't support userPassword in ADD)
            attrs: dict[str, Any] = {
                "objectClass": [self.config.user_object_class],
                self.config.username_attribute: username,
                self.config.email_attribute: email,
            }

            # Create the user entry
            success = conn.add(user_dn, attributes=attrs)

            if not success:
                conn.unbind()
                return False, f"Failed to create user: {conn.result}"

            # Set password using LDAP Password Modify Extended Operation (RFC 3062)
            # Required for LLDAP - service account must be in lldap_password_manager group
            try:
                password_success = conn.extend.standard.modify_password(
                    user_dn, None, password
                )
                if not password_success:
                    logger.error(
                        "Failed to set password for new user %s. "
                        "Ensure service account is in lldap_password_manager group. Result: %s",
                        user_dn,
                        conn.result,
                    )
                    conn.unbind()
                    return (
                        False,
                        f"User created but password not set. Service account needs lldap_password_manager group membership: {conn.result}",
                    )
            except Exception as e:
                logger.exception("Password set failed for new user %s", user_dn)
                conn.unbind()
                return False, f"User created but password set failed: {e}"

            conn.unbind()
            logger.info("Created LDAP user with password: %s", user_dn)
            return True, user_dn

        except LDAPInvalidDnError as e:
            logger.exception("Invalid DN when creating/updating user")
            return False, f"Invalid DN: {e}"
        except LDAPException as e:
            logger.exception("Error creating/updating LDAP user")
            return False, f"LDAP error: {e}"

    def delete_user(self, user_dn: str) -> tuple[bool, str]:
        if not user_dn:
            return False, "User DN is required"

        try:
            conn = self._service_connection()
            if not conn:
                return False, "Cannot connect to LDAP server"

            # Attempt to delete the user
            success = conn.delete(user_dn)

            if not success:
                error_msg = f"Failed to delete LDAP user: {conn.result}"
                logger.error(error_msg)
                conn.unbind()
                return False, error_msg

            conn.unbind()
            logger.info("Deleted LDAP user: %s", user_dn)
            return True, "User deleted successfully"

        except LDAPInvalidDnError as e:
            logger.exception("Invalid DN when deleting user: %s", user_dn)
            return False, f"Invalid DN: {e}"
        except LDAPException as e:
            logger.exception("Error deleting LDAP user: %s", user_dn)
            return False, f"LDAP error: {e}"
        except Exception as e:
            logger.exception("Unexpected error deleting LDAP user: %s", user_dn)
            return False, f"Unexpected error: {e}"

    def change_password(self, user_dn: str, new_password: str) -> tuple[bool, str]:
        if not user_dn:
            return False, "User DN is required"

        if not new_password:
            return False, "New password is required"

        try:
            conn = self._service_connection()
            if not conn:
                return False, "Cannot connect to LDAP server"

            # Use LDAP Password Modify Extended Operation (RFC 3062)
            # Required for LLDAP - service account must be in lldap_password_manager group
            success = conn.extend.standard.modify_password(user_dn, None, new_password)

            if not success:
                error_msg = f"Failed to change password. Ensure service account is in lldap_password_manager group. Result: {conn.result}"
                logger.error(error_msg)
                conn.unbind()
                return False, error_msg

            conn.unbind()
            logger.info("Changed password for LDAP user: %s", user_dn)
            return True, "Password changed successfully"

        except LDAPException as e:
            logger.exception("Error changing LDAP user password: %s", user_dn)
            return False, f"LDAP error: {e}"
        except Exception as e:
            logger.exception("Unexpected error changing password: %s", user_dn)
            return False, f"Unexpected error: {e}"

    def search_groups(self, search_filter: str | None = None) -> list[dict]:
        if not self.config.group_base_dn:
            logger.warning("group_base_dn not configured - cannot search for groups")
            return []

        try:
            conn = self._service_connection()
            if not conn:
                logger.error(
                    "Failed to establish service account connection for group search"
                )
                return []

            filter_str = (
                search_filter or f"(objectClass={self.config.group_object_class})"
            )

            logger.info(
                "Searching for LDAP groups: base_dn=%s, filter=%s",
                self.config.group_base_dn,
                filter_str,
            )

            success = conn.search(
                search_base=self.config.group_base_dn,
                search_filter=filter_str,
                search_scope=SUBTREE,
                attributes=["cn"],
            )

            if not success:
                logger.warning(
                    "LDAP group search failed: %s (result: %s)",
                    conn.result.get("description", "Unknown error"),
                    conn.result,
                )
                conn.unbind()
                return []

            logger.info("Found %d group entries", len(conn.entries))

            groups = [
                {
                    "dn": str(entry.entry_dn),
                    "cn": str(entry.cn.value) if hasattr(entry, "cn") else "",
                    "description": None,
                }
                for entry in conn.entries
            ]

            conn.unbind()
            return groups

        except LDAPException as e:
            logger.exception("Error searching LDAP groups: %s", e)
            return []

    def get_user_groups(self, user_dn: str) -> list[dict]:
        """Get groups where user is a member. Requires group_base_dn."""
        if not self.config.group_base_dn:
            logger.warning(
                "group_base_dn not configured - cannot check group membership. "
                "Configure Group Base DN in LDAP settings to enable group-based authorization."
            )
            return []

        try:
            conn = self._service_connection()
            if not conn:
                return []

            # Search for groups where user is a member
            # For LLDAP: objectClass=groupOfUniqueNames, member attribute=uniqueMember
            member_filter = f"({self.config.group_member_attribute}={user_dn})"
            object_class_filter = f"(objectClass={self.config.group_object_class})"
            search_filter = f"(&{object_class_filter}{member_filter})"

            conn.search(
                search_base=self.config.group_base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=["cn"],
            )

            groups = [
                {
                    "dn": str(entry.entry_dn),
                    "cn": str(entry.cn.value) if hasattr(entry, "cn") else "",
                }
                for entry in conn.entries
            ]

            logger.info(f"Found {len(groups)} groups for user {user_dn}")
            conn.unbind()
            return groups

        except LDAPException:
            logger.exception("Error fetching user groups")
            return []

    def _service_connection(self) -> Connection | None:
        try:
            if not self.config.service_account_dn:
                logger.error("Service account DN not configured")
                return None

            password = decrypt_credential(
                self.config.service_account_password_encrypted or ""
            )
            if not password:
                logger.error("Service account password not configured")
                return None

            return Connection(
                self._server,
                user=self.config.service_account_dn,
                password=password,
                auto_bind=True,
            )

        except LDAPException:
            logger.exception("Error connecting with service account")
            return None
