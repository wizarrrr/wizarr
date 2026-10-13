from unittest.mock import patch

import pytest

from app.models import Invitation, LDAPConfiguration, MediaServer
from app.services.invites import create_invite
from app.services.ldap.invitation_ldap import InvitationLDAPHandler


@pytest.fixture
def ldap_config(session):
    config = LDAPConfiguration(
        enabled=True,
        server_url="ldap://ldap.example.com:389",
        service_account_dn="cn=wizarr,ou=people,dc=example,dc=com",
        service_account_password_encrypted="encrypted_password",
        user_base_dn="ou=people,dc=example,dc=com",
        user_search_filter="(uid={username})",
        username_attribute="uid",
        email_attribute="mail",
        user_object_class="inetOrgPerson",
    )
    session.add(config)
    session.commit()
    yield config
    # The session fixture does not delete the LDAP configuration.
    LDAPConfiguration.query.delete()
    session.commit()


@pytest.mark.parametrize(
    ("ldap_enabled", "requested", "expected"),
    [(True, True, True), (False, True, False), (True, False, False)],
)
def test_should_create_ldap_user(
    session, ldap_config, ldap_enabled, requested, expected
):
    ldap_config.enabled = ldap_enabled
    session.commit()
    invitation = Invitation(code="TESTCODE", create_ldap_user=requested)

    assert InvitationLDAPHandler(invitation).should_create_ldap_user() is expected


@pytest.mark.parametrize(
    "outcome",
    [
        (True, "uid=testuser,ou=people,dc=example,dc=com"),
        (False, "LDAP error: User exists"),
    ],
)
@patch("app.services.ldap.invitation_ldap.LDAPClient")
def test_create_ldap_user_returns_the_client_result(
    mock_client_class, ldap_config, outcome
):
    client = mock_client_class.return_value
    client.create_user.return_value = outcome
    invitation = Invitation(code="TESTCODE", create_ldap_user=True)

    result = InvitationLDAPHandler(invitation).create_ldap_user(
        username="testuser", email="test@example.com", password="password123"
    )

    assert result == outcome
    client.create_user.assert_called_once_with(
        username="testuser", email="test@example.com", password="password123"
    )


@pytest.mark.parametrize(("checkbox", "expected"), [("true", True), ("", False)])
def test_create_invite_stores_ldap_choice(session, checkbox, expected):
    server = MediaServer(
        name="Test Server", server_type="jellyfin", url="http://localhost:8096"
    )
    session.add(server)
    session.commit()

    invitation = create_invite(
        {
            "code": "LDAPTEST",
            "expires": "never",
            "server_ids": [str(server.id)],
            "create_ldap_user": checkbox,
        }
    )

    assert invitation.create_ldap_user is expected
