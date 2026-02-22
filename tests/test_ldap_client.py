from unittest.mock import MagicMock, patch

import pytest

from app.models import LDAPConfiguration
from app.services.ldap.client import LDAPClient


@pytest.fixture
def ldap_config():
    from app.services.ldap.encryption import encrypt_credential

    config = LDAPConfiguration()
    config.server_url = "ldap://ldap.example.com:389"
    config.use_tls = True
    config.verify_cert = True
    config.service_account_dn = "cn=wizarr,ou=people,dc=example,dc=com"
    # Use a properly encrypted password for testing
    config.service_account_password_encrypted = encrypt_credential("test_password")
    config.user_base_dn = "ou=people,dc=example,dc=com"
    config.user_search_filter = "(uid={username})"
    config.username_attribute = "uid"
    config.email_attribute = "mail"
    config.user_object_class = "inetOrgPerson"
    config.group_base_dn = "ou=groups,dc=example,dc=com"
    config.group_object_class = "groupOfUniqueNames"
    config.group_member_attribute = "uniqueMember"
    return config


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_test_connection_success(mock_server, mock_connection, ldap_config):
    """Test successful LDAP connection test."""
    mock_conn = MagicMock()
    mock_connection.return_value = mock_conn

    client = LDAPClient(ldap_config)
    success, message = client.test_connection()

    assert success is True
    assert message == "Connection successful"
    mock_conn.unbind.assert_called_once()


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_test_connection_bind_error(mock_server, mock_connection, ldap_config):
    from ldap3.core.exceptions import LDAPBindError

    mock_connection.side_effect = LDAPBindError("Invalid credentials")

    client = LDAPClient(ldap_config)
    success, message = client.test_connection()

    assert success is False
    assert "Authentication failed" in message


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_authenticate_user_success(mock_server, mock_connection, ldap_config):
    # Mock service account connection for DN lookup
    mock_service_conn = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_dn = "uid=testuser,ou=people,dc=example,dc=com"
    mock_service_conn.entries = [mock_entry]

    # Mock user connection for authentication
    mock_user_conn = MagicMock()
    mock_user_entry = MagicMock()
    mock_user_entry.entry_dn = "uid=testuser,ou=people,dc=example,dc=com"
    mock_user_entry.uid.value = "testuser"
    mock_user_entry.mail.value = "test@example.com"
    mock_user_conn.entries = [mock_user_entry]

    # Return service conn first, then user conn
    mock_connection.side_effect = [mock_service_conn, mock_user_conn]

    client = LDAPClient(ldap_config)
    success, attrs = client.authenticate_user("testuser", "userpassword")

    assert success is True
    assert "uid" in attrs
    assert attrs["uid"] == "testuser"


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_create_user_success(mock_server, mock_connection, ldap_config):
    mock_conn = MagicMock()
    mock_conn.add.return_value = True
    mock_conn.extend.standard.modify_password.return_value = True
    mock_conn.search.return_value = False
    mock_conn.entries = []
    mock_connection.return_value = mock_conn

    client = LDAPClient(ldap_config)
    success, result = client.create_user(
        username="newuser",
        email="newuser@example.com",
        password="password123",
    )

    assert success is True
    assert "uid=newuser,ou=people,dc=example,dc=com" in result
    mock_conn.add.assert_called_once()
    mock_conn.extend.standard.modify_password.assert_called_once()
    mock_conn.unbind.assert_called_once()


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_search_groups(mock_server, mock_connection, ldap_config):
    mock_conn = MagicMock()
    mock_conn.search.return_value = True

    # Mock group entries
    mock_entry1 = MagicMock()
    mock_entry1.entry_dn = "cn=users,ou=groups,dc=example,dc=com"
    mock_entry1.cn.value = "users"

    mock_entry2 = MagicMock()
    mock_entry2.entry_dn = "cn=admins,ou=groups,dc=example,dc=com"
    mock_entry2.cn.value = "admins"

    mock_conn.entries = [mock_entry1, mock_entry2]
    mock_connection.return_value = mock_conn

    client = LDAPClient(ldap_config)
    groups = client.search_groups()

    assert len(groups) == 2
    assert groups[0]["cn"] == "users"
    assert groups[0]["description"] is None
    assert groups[1]["cn"] == "admins"
    assert groups[1]["description"] is None
    mock_conn.search.assert_called_once()
    mock_conn.unbind.assert_called_once()


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_delete_user_success(mock_server, mock_connection, ldap_config):
    """Test successful LDAP user deletion."""
    mock_conn = MagicMock()
    mock_conn.delete.return_value = True
    mock_connection.return_value = mock_conn

    client = LDAPClient(ldap_config)
    user_dn = "uid=testuser,ou=people,dc=example,dc=com"
    success, message = client.delete_user(user_dn)

    assert success is True
    assert message == "User deleted successfully"
    mock_conn.delete.assert_called_once_with(user_dn)
    mock_conn.unbind.assert_called_once()


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_delete_user_failure(mock_server, mock_connection, ldap_config):
    """Test failed LDAP user deletion."""
    mock_conn = MagicMock()
    mock_conn.delete.return_value = False
    mock_conn.result = {"description": "No such object"}
    mock_connection.return_value = mock_conn

    client = LDAPClient(ldap_config)
    user_dn = "uid=nonexistent,ou=people,dc=example,dc=com"
    success, message = client.delete_user(user_dn)

    assert success is False
    assert "Failed to delete LDAP user" in message
    mock_conn.unbind.assert_called_once()


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_delete_user_missing_dn(mock_server, mock_connection, ldap_config):
    """Test LDAP user deletion with missing DN."""
    client = LDAPClient(ldap_config)
    success, message = client.delete_user("")

    assert success is False
    assert message == "User DN is required"


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_change_password_success(mock_server, mock_connection, ldap_config):
    """Test successful LDAP password change."""
    mock_conn = MagicMock()
    mock_conn.extend.standard.modify_password.return_value = True
    mock_connection.return_value = mock_conn

    client = LDAPClient(ldap_config)
    user_dn = "uid=testuser,ou=people,dc=example,dc=com"
    success, message = client.change_password(user_dn, "newpassword123")

    assert success is True
    assert message == "Password changed successfully"
    mock_conn.extend.standard.modify_password.assert_called_once_with(
        user_dn, None, "newpassword123"
    )
    mock_conn.unbind.assert_called_once()


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_change_password_failure(mock_server, mock_connection, ldap_config):
    """Test failed LDAP password change."""
    mock_conn = MagicMock()
    mock_conn.extend.standard.modify_password.return_value = False
    mock_conn.result = {"description": "Insufficient access rights"}
    mock_connection.return_value = mock_conn

    client = LDAPClient(ldap_config)
    user_dn = "uid=testuser,ou=people,dc=example,dc=com"
    success, message = client.change_password(user_dn, "newpassword123")

    assert success is False
    assert "Failed to change password" in message
    assert "lldap_password_manager" in message
    mock_conn.unbind.assert_called_once()


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_change_password_missing_dn(mock_server, mock_connection, ldap_config):
    """Test LDAP password change with missing DN."""
    client = LDAPClient(ldap_config)
    success, message = client.change_password("", "newpassword123")

    assert success is False
    assert message == "User DN is required"


@patch("app.services.ldap.client.Connection")
@patch("app.services.ldap.client.Server")
def test_change_password_missing_password(mock_server, mock_connection, ldap_config):
    """Test LDAP password change with missing password."""
    client = LDAPClient(ldap_config)
    user_dn = "uid=testuser,ou=people,dc=example,dc=com"
    success, message = client.change_password(user_dn, "")

    assert success is False
    assert message == "New password is required"
