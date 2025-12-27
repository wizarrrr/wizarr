from flask import current_app, session
from flask_login import login_user

from app.extensions import db
from app.models import AdminAccount, LDAPConfiguration
from app.services.ldap.client import LDAPClient


def handle_ldap_login(username: str, password: str) -> tuple[bool, str]:
    # Get LDAP configuration
    ldap_config = LDAPConfiguration.query.first()

    if not ldap_config or not ldap_config.enabled:
        return False, "LDAP authentication is not enabled"

    if not ldap_config.allow_admin_bind:
        return False, "LDAP admin authentication is not allowed"

    # Authenticate via LDAP
    client = LDAPClient(ldap_config)

    try:
        success, user_attrs = client.authenticate_user(username, password)

        if not success:
            current_app.logger.warning(
                f"LDAP authentication failed for user: {username}"
            )
            return False, "Invalid LDAP credentials"

        # Get user DN and attributes
        user_dn = user_attrs.get("dn")
        if not user_dn:
            current_app.logger.warning(f"LDAP user DN not found for user: {username}")
            return False, "User DN not found in LDAP response"
        # Check admin group membership if required
        if ldap_config.admin_group_dn:
            groups = client.get_user_groups(user_dn)
            group_dns = [g.get("dn").lower() for g in groups if g.get("dn")]

            # Normalize admin group DN for comparison (case-insensitive)
            admin_group_dn_lower = ldap_config.admin_group_dn.lower()

            if admin_group_dn_lower not in group_dns:
                current_app.logger.warning(
                    f"User {username} not in admin group. "
                    f"Required: {ldap_config.admin_group_dn}, "
                    f"User groups: {[g.get('dn') for g in groups]}"
                )
                return False, "User is not authorized as an administrator"

        # Find existing admin account by username
        # LDAP authentication allows logging into existing local accounts
        admin = AdminAccount.query.filter_by(username=username).first()

        if not admin:
            # Create new admin account if none exists
            admin = AdminAccount(username=username)
            admin.auth_source = "local"  # Default to local, can use both methods
            admin.password_hash = None  # No local password set initially
            admin.external_id = user_dn
            admin.email = user_attrs.get(ldap_config.email_attribute)

            db.session.add(admin)
            db.session.commit()
            current_app.logger.info(
                f"Created new admin account '{username}' via LDAP (supports both auth methods)"
            )
        # Update existing account with LDAP attributes
        # This syncs the external_id and email on every LDAP login
        else:
            needs_update = False
            if admin.external_id != user_dn:
                current_app.logger.info(
                    f"Updating LDAP DN for account '{username}': {admin.external_id} -> {user_dn}"
                )
                admin.external_id = user_dn
                needs_update = True

            ldap_email = user_attrs.get(ldap_config.email_attribute)
            if ldap_email and admin.email != ldap_email:
                admin.email = ldap_email
                needs_update = True

            if needs_update:
                db.session.commit()

        # Log the user in
        login_user(admin)
        session.permanent = True

        current_app.logger.info(
            f"LDAP admin login successful: {username} (DN: {user_dn})"
        )
        return True, "Login successful"

    except Exception as e:
        current_app.logger.error(f"LDAP authentication error: {e}")
        # Rollback any pending transaction
        db.session.rollback()
        return False, "LDAP authentication failed"
