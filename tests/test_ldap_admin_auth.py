"""Unit tests for LDAP admin authentication."""

from unittest.mock import MagicMock, patch

import pytest

from app.extensions import db
from app.models import AdminAccount, LDAPConfiguration


@pytest.fixture
def ldap_config_with_admin(app):
    """Create LDAP configuration with admin authentication enabled."""
    from app.services.ldap.encryption import encrypt_credential

    with app.app_context():
        config = LDAPConfiguration(
            enabled=True,
            server_url="ldap://ldap.example.com:389",
            use_tls=True,
            verify_cert=True,
            service_account_dn="cn=wizarr,ou=people,dc=example,dc=com",
            service_account_password_encrypted=encrypt_credential("test_password"),
            user_base_dn="ou=people,dc=example,dc=com",
            user_search_filter="(uid={username})",
            username_attribute="uid",
            email_attribute="mail",
            user_object_class="inetOrgPerson",
            group_base_dn="ou=groups,dc=example,dc=com",
            group_object_class="groupOfUniqueNames",
            group_member_attribute="uniqueMember",
            allow_admin_bind=True,
            admin_group_dn="cn=admins,ou=groups,dc=example,dc=com",
        )
        db.session.add(config)
        db.session.commit()
        yield config
        db.session.delete(config)
        db.session.commit()


@patch("app.blueprints.auth.ldap_auth.LDAPClient")
def test_ldap_admin_login_success(mock_client_class, app, ldap_config_with_admin):
    """Test successful LDAP admin authentication."""
    from app.blueprints.auth.ldap_auth import handle_ldap_login

    with app.app_context():
        # Mock LDAP client
        mock_client = MagicMock()
        mock_client.authenticate_user.return_value = (
            True,
            {
                "dn": "uid=admin,ou=people,dc=example,dc=com",
                "uid": "admin",
                "mail": "admin@example.com",
            },
        )
        mock_client.get_user_groups.return_value = [
            {"dn": "cn=admins,ou=groups,dc=example,dc=com", "cn": "admins"}
        ]
        mock_client_class.return_value = mock_client

        # Perform login
        success, message = handle_ldap_login("admin", "password123")

        assert success is True
        assert message == "Login successful"

        # Verify admin account was created
        admin = AdminAccount.query.filter_by(username="admin").first()
        assert admin is not None
        assert admin.username == "admin"
        assert admin.email == "admin@example.com"
        assert admin.auth_source == "local"  # Supports both local and LDAP auth
        assert admin.external_id == "uid=admin,ou=people,dc=example,dc=com"

        # Cleanup
        db.session.delete(admin)
        db.session.commit()


@patch("app.blueprints.auth.ldap_auth.LDAPClient")
def test_ldap_admin_login_invalid_credentials(
    mock_client_class, app, ldap_config_with_admin
):
    """Test LDAP admin login with invalid credentials."""
    from app.blueprints.auth.ldap_auth import handle_ldap_login

    with app.app_context():
        # Mock LDAP client
        mock_client = MagicMock()
        mock_client.authenticate_user.return_value = (False, {})
        mock_client_class.return_value = mock_client

        # Perform login
        success, message = handle_ldap_login("admin", "wrongpassword")

        assert success is False
        assert "Invalid LDAP credentials" in message


@patch("app.blueprints.auth.ldap_auth.LDAPClient")
def test_ldap_admin_login_not_in_admin_group(
    mock_client_class, app, ldap_config_with_admin
):
    """Test LDAP admin login when user is not in admin group."""
    from app.blueprints.auth.ldap_auth import handle_ldap_login

    with app.app_context():
        # Mock LDAP client
        mock_client = MagicMock()
        mock_client.authenticate_user.return_value = (
            True,
            {
                "dn": "uid=user,ou=people,dc=example,dc=com",
                "uid": "user",
                "mail": "user@example.com",
            },
        )
        # User is not in admin group
        mock_client.get_user_groups.return_value = [
            {"dn": "cn=users,ou=groups,dc=example,dc=com", "cn": "users"}
        ]
        mock_client_class.return_value = mock_client

        # Perform login
        success, message = handle_ldap_login("user", "password123")

        assert success is False
        assert "not authorized as an administrator" in message


@patch("app.blueprints.auth.ldap_auth.LDAPClient")
def test_ldap_admin_login_existing_account(
    mock_client_class, app, ldap_config_with_admin
):
    """Test LDAP admin login with existing account (email update)."""
    from app.blueprints.auth.ldap_auth import handle_ldap_login

    with app.app_context():
        # Create existing admin account
        existing_admin = AdminAccount(username="admin")
        existing_admin.auth_source = "ldap"
        existing_admin.external_id = "uid=admin,ou=people,dc=example,dc=com"
        existing_admin.email = "old@example.com"
        db.session.add(existing_admin)
        db.session.commit()

        # Mock LDAP client
        mock_client = MagicMock()
        mock_client.authenticate_user.return_value = (
            True,
            {
                "dn": "uid=admin,ou=people,dc=example,dc=com",
                "uid": "admin",
                "mail": "new@example.com",
            },
        )
        mock_client.get_user_groups.return_value = [
            {"dn": "cn=admins,ou=groups,dc=example,dc=com", "cn": "admins"}
        ]
        mock_client_class.return_value = mock_client

        # Perform login
        success, message = handle_ldap_login("admin", "password123")

        assert success is True
        assert message == "Login successful"

        # Verify email was updated
        admin = AdminAccount.query.filter_by(
            auth_source="ldap",
            external_id="uid=admin,ou=people,dc=example,dc=com",
        ).first()
        assert admin is not None
        assert admin.email == "new@example.com"

        # Cleanup
        db.session.delete(admin)
        db.session.commit()


def test_ldap_admin_login_disabled(app):
    """Test LDAP admin login when LDAP is disabled."""
    from app.blueprints.auth.ldap_auth import handle_ldap_login

    with app.app_context():
        # No LDAP config
        success, message = handle_ldap_login("admin", "password123")

        assert success is False
        assert "not enabled" in message


def test_ldap_admin_login_bind_not_allowed(app):
    """Test LDAP admin login when admin bind is not allowed."""
    from app.services.ldap.encryption import encrypt_credential

    with app.app_context():
        config = LDAPConfiguration(
            enabled=True,
            server_url="ldap://ldap.example.com:389",
            use_tls=True,
            service_account_dn="cn=wizarr,ou=people,dc=example,dc=com",
            service_account_password_encrypted=encrypt_credential("test_password"),
            user_base_dn="ou=people,dc=example,dc=com",
            user_search_filter="(uid={username})",
            username_attribute="uid",
            email_attribute="mail",
            user_object_class="inetOrgPerson",
            group_base_dn="ou=groups,dc=example,dc=com",
            group_object_class="groupOfUniqueNames",
            group_member_attribute="uniqueMember",
            allow_admin_bind=False,  # Admin bind disabled
        )
        db.session.add(config)
        db.session.commit()

        from app.blueprints.auth.ldap_auth import handle_ldap_login

        success, message = handle_ldap_login("admin", "password123")

        assert success is False
        assert "not allowed" in message

        # Cleanup
        db.session.delete(config)
        db.session.commit()
