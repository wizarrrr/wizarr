"""Unit tests for LDAP admin authentication."""

from unittest.mock import patch

import pytest

from app.blueprints.auth.ldap_auth import handle_ldap_login
from app.models import AdminAccount, LDAPConfiguration
from app.services.ldap.encryption import encrypt_credential


@pytest.fixture
def ldap_config(session):
    """Create LDAP configuration with admin authentication enabled."""
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
    session.add(config)
    session.commit()
    yield config
    # The session fixture does not delete the LDAP configuration.
    LDAPConfiguration.query.delete()
    session.commit()


@pytest.fixture
def ldap_client():
    """Patch the LDAP client that the login handler makes."""
    with patch("app.blueprints.auth.ldap_auth.LDAPClient") as client_class:
        yield client_class.return_value


def ldap_user(client, uid, mail, group="admins"):
    """Make the LDAP client accept the user, as a member of one group."""
    client.authenticate_user.return_value = (
        True,
        {"dn": f"uid={uid},ou=people,dc=example,dc=com", "uid": uid, "mail": mail},
    )
    client.get_user_groups.return_value = [
        {"dn": f"cn={group},ou=groups,dc=example,dc=com", "cn": group}
    ]


def test_ldap_admin_login_success(ldap_config, ldap_client):
    ldap_user(ldap_client, "admin", "admin@example.com")

    success, message = handle_ldap_login("admin", "password123")

    assert success is True
    assert message == "Login successful"
    admin = AdminAccount.query.filter_by(username="admin").first()
    assert admin is not None
    assert admin.email == "admin@example.com"
    assert admin.auth_source == "local"  # Supports both local and LDAP auth
    assert admin.external_id == "uid=admin,ou=people,dc=example,dc=com"


def test_ldap_admin_login_invalid_credentials(ldap_config, ldap_client):
    ldap_client.authenticate_user.return_value = (False, {})

    success, message = handle_ldap_login("admin", "wrongpassword")

    assert success is False
    assert "Invalid LDAP credentials" in message


def test_ldap_admin_login_not_in_admin_group(ldap_config, ldap_client):
    ldap_user(ldap_client, "user", "user@example.com", group="users")

    success, message = handle_ldap_login("user", "password123")

    assert success is False
    assert "not authorized as an administrator" in message


def test_ldap_admin_login_existing_account(session, ldap_config, ldap_client):
    """An LDAP login updates the email of an existing account."""
    existing_admin = AdminAccount(username="admin")
    existing_admin.auth_source = "ldap"
    existing_admin.external_id = "uid=admin,ou=people,dc=example,dc=com"
    existing_admin.email = "old@example.com"
    session.add(existing_admin)
    session.commit()
    ldap_user(ldap_client, "admin", "new@example.com")

    success, message = handle_ldap_login("admin", "password123")

    assert success is True
    assert message == "Login successful"
    admin = AdminAccount.query.filter_by(
        auth_source="ldap",
        external_id="uid=admin,ou=people,dc=example,dc=com",
    ).first()
    assert admin is not None
    assert admin.email == "new@example.com"


def test_ldap_admin_login_disabled(session):
    success, message = handle_ldap_login("admin", "password123")

    assert success is False
    assert "not enabled" in message


def test_ldap_admin_login_bind_not_allowed(session, ldap_config):
    ldap_config.allow_admin_bind = False
    session.commit()

    success, message = handle_ldap_login("admin", "password123")

    assert success is False
    assert "not allowed" in message


@pytest.mark.parametrize(
    ("authenticated", "status"),
    [(True, 302), (False, 200)],
)
def test_login_route_with_ldap(client, ldap_config, ldap_client, authenticated, status):
    ldap_user(ldap_client, "admin", "admin@example.com")
    if not authenticated:
        ldap_client.authenticate_user.return_value = (False, {})

    response = client.post(
        "/login",
        data={"username": "admin", "password": "secret", "auth_method": "ldap"},
    )

    assert response.status_code == status
    body = response.get_data(as_text=True)
    assert ("Invalid LDAP credentials" in body) is not authenticated
    with client.session_transaction() as sess:
        assert ("_user_id" in sess) is authenticated
