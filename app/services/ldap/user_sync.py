"""LDAP user synchronization and conversion utilities."""

import logging
from typing import Any

from app.extensions import db
from app.models import LDAPConfiguration, User
from app.services.ldap.client import LDAPClient

logger = logging.getLogger(__name__)


def list_ldap_users() -> tuple[bool, list[dict[str, Any]] | str]:
    try:
        ldap_config = LDAPConfiguration.query.filter_by(enabled=True).first()
        if not ldap_config:
            return False, "LDAP is not configured"

        client = LDAPClient(ldap_config)
        conn = client._service_connection()
        if not conn:
            return False, "Cannot connect to LDAP server"

        # Search for all users
        search_filter = f"(objectClass={ldap_config.user_object_class})"
        success = conn.search(
            search_base=ldap_config.user_base_dn,
            search_filter=search_filter,
            attributes=[
                ldap_config.username_attribute,
                ldap_config.email_attribute,
            ],
        )

        if not success:
            conn.unbind()
            return False, f"LDAP search failed: {conn.result}"

        users = []
        for entry in conn.entries:
            username = getattr(entry, ldap_config.username_attribute, None)
            email = getattr(entry, ldap_config.email_attribute, None)

            # Get the value (ldap3 returns single values directly)
            username = username.value if hasattr(username, "value") else username
            email = email.value if hasattr(email, "value") else email

            if username:
                users.append(
                    {
                        "username": str(username),
                        "email": str(email) if email else f"{username}@ldap.local",
                        "dn": str(entry.entry_dn),
                    }
                )

        conn.unbind()
        logger.info("Found %d users in LDAP", len(users))
        return True, users

    except Exception as e:
        logger.exception("Error listing LDAP users")
        return False, f"Error: {e}"


def import_ldap_user(username: str) -> tuple[bool, str]:
    try:
        ldap_config = LDAPConfiguration.query.filter_by(enabled=True).first()
        if not ldap_config:
            return False, "LDAP is not configured"

        # Check if user already exists in Wizarr
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return False, f"User {username} already exists in Wizarr"

        # Verify user exists in LDAP
        client = LDAPClient(ldap_config)
        user_dn = client._find_user_dn(username)
        if not user_dn:
            return False, f"User {username} not found in LDAP"

        # Fetch user attributes
        conn = client._service_connection()
        if not conn:
            return False, "Cannot connect to LDAP server"

        conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            attributes=[ldap_config.username_attribute, ldap_config.email_attribute],
        )

        if not conn.entries:
            conn.unbind()
            return False, f"Could not fetch user details for {username}"

        entry = conn.entries[0]
        email_attr = getattr(entry, ldap_config.email_attribute, None)
        email = email_attr.value if hasattr(email_attr, "value") else email_attr
        conn.unbind()

        # Create User record without server association
        # This user won't have media server access until admin assigns them
        # Generate a placeholder token (UUID) since token is required but user has no server yet
        import uuid

        new_user = User(
            username=username,
            email=str(email) if email else f"{username}@ldap.local",
            token=str(uuid.uuid4()),  # Placeholder token until assigned to server
            code="",  # No invitation code for direct LDAP imports
            is_ldap_user=True,
            # No server_id - admin must manually assign to servers
        )
        db.session.add(new_user)
        db.session.commit()

        logger.info(
            "Imported LDAP user %s (no server assignment, admin must assign)", username
        )
        return (
            True,
            f"User {username} imported successfully. Admin must assign to media servers.",
        )

    except Exception as e:
        db.session.rollback()
        logger.exception("Error importing LDAP user %s", username)
        return False, f"Error: {e}"


def convert_user_to_ldap(user_id: int, create_in_ldap: bool = True) -> tuple[bool, str]:
    try:
        user = db.session.get(User, user_id)
        if not user:
            return False, f"User with ID {user_id} not found"

        if user.is_ldap_user:
            return False, f"User {user.username} is already an LDAP user"

        ldap_config = LDAPConfiguration.query.filter_by(enabled=True).first()
        if not ldap_config:
            return False, "LDAP is not configured"

        if create_in_ldap:
            # Create user in LDAP
            # Note: We can't migrate the password, user must reset it
            client = LDAPClient(ldap_config)

            # Generate a temporary random password
            import secrets

            temp_password = secrets.token_urlsafe(32)

            success, result = client.create_user(
                username=user.username,
                email=user.email or f"{user.username}@ldap.local",
                password=temp_password,
            )

            if not success:
                return False, f"Failed to create LDAP user: {result}"

            logger.info(
                "Created LDAP user for %s with temporary password", user.username
            )

        # Mark all User records with this username as LDAP users
        User.query.filter_by(username=user.username).update(
            {"is_ldap_user": True}, synchronize_session=False
        )
        db.session.commit()

        message = (
            f"User {user.username} converted to LDAP user. "
            f"{'User created in LDAP with temporary password - password reset required.' if create_in_ldap else 'User must exist in LDAP.'}"
        )
        logger.info(message)
        return True, message

    except Exception as e:
        db.session.rollback()
        logger.exception("Error converting user %s to LDAP", user_id)
        return False, f"Error: {e}"
