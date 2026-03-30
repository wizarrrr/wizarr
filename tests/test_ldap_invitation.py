from unittest.mock import MagicMock, patch

import pytest

from app.extensions import db
from app.models import Invitation, LDAPConfiguration
from app.services.ldap.invitation_ldap import InvitationLDAPHandler


@pytest.fixture
def ldap_config(app):
    with app.app_context():
        config = LDAPConfiguration(
            enabled=True,
            server_url="ldap://ldap.example.com:389",
            use_tls=True,
            verify_cert=True,
            service_account_dn="cn=wizarr,ou=people,dc=example,dc=com",
            service_account_password_encrypted="encrypted_password",
            user_base_dn="ou=people,dc=example,dc=com",
            user_search_filter="(uid={username})",
            username_attribute="uid",
            email_attribute="mail",
            user_object_class="inetOrgPerson",
            group_base_dn="ou=groups,dc=example,dc=com",
            group_object_class="groupOfUniqueNames",
            group_member_attribute="uniqueMember",
        )
        db.session.add(config)
        db.session.commit()
        yield config
        db.session.delete(config)
        db.session.commit()


@pytest.fixture
def invitation_with_ldap(app, ldap_config):
    with app.app_context():
        invitation = Invitation(
            code="TESTCODE",
            create_ldap_user=True,
        )
        db.session.add(invitation)
        db.session.commit()
        yield invitation
        db.session.delete(invitation)
        db.session.commit()


def test_should_create_ldap_user_enabled(app, ldap_config, invitation_with_ldap):
    with app.app_context():
        handler = InvitationLDAPHandler(invitation_with_ldap)
        assert handler.should_create_ldap_user() is True


def test_should_create_ldap_user_disabled(app, invitation_with_ldap):
    with app.app_context():
        # Disable LDAP
        config = LDAPConfiguration.query.first()
        config.enabled = False
        db.session.commit()

        handler = InvitationLDAPHandler(invitation_with_ldap)
        assert handler.should_create_ldap_user() is False


def test_should_create_ldap_user_not_requested(app, ldap_config):
    with app.app_context():
        invitation = Invitation(
            code="TESTCODE2",
            create_ldap_user=False,
        )
        db.session.add(invitation)
        db.session.commit()

        handler = InvitationLDAPHandler(invitation)
        assert handler.should_create_ldap_user() is False

        db.session.delete(invitation)
        db.session.commit()


@patch("app.services.ldap.invitation_ldap.LDAPClient")
def test_create_ldap_user_success(
    mock_client_class, app, ldap_config, invitation_with_ldap
):
    with app.app_context():
        mock_client = MagicMock()
        mock_client.create_user.return_value = (
            True,
            "uid=testuser,ou=people,dc=example,dc=com",
        )
        mock_client_class.return_value = mock_client

        handler = InvitationLDAPHandler(invitation_with_ldap)
        success, result = handler.create_ldap_user(
            username="testuser",
            email="test@example.com",
            password="password123",
        )

        assert success is True
        assert "uid=testuser" in result

        # Verify client methods were called
        mock_client.create_user.assert_called_once_with(
            username="testuser",
            email="test@example.com",
            password="password123",
        )


@patch("app.services.ldap.invitation_ldap.LDAPClient")
def test_create_ldap_user_failure(
    mock_client_class, app, ldap_config, invitation_with_ldap
):
    with app.app_context():
        mock_client = MagicMock()
        mock_client.create_user.return_value = (False, "LDAP error: User exists")
        mock_client_class.return_value = mock_client

        handler = InvitationLDAPHandler(invitation_with_ldap)
        success, result = handler.create_ldap_user(
            username="testuser",
            email="test@example.com",
            password="password123",
        )

        assert success is False
        assert "LDAP error" in result
