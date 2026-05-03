import pytest

from app.extensions import db
from app.models import LDAPConfiguration, LDAPGroup, MediaServer
from app.services.invites import create_invite


@pytest.fixture
def ldap_setup(app):
    with app.app_context():
        config = LDAPConfiguration(
            enabled=True,
            server_url="ldap://ldap.example.com:389",
            use_tls=True,
            service_account_dn="cn=wizarr,ou=people,dc=example,dc=com",
            service_account_password_encrypted="encrypted_password",
            user_base_dn="ou=people,dc=example,dc=com",
            user_search_filter="(uid={username})",
            username_attribute="uid",
            email_attribute="mail",
            user_object_class="inetOrgPerson",
        )
        db.session.add(config)

        group1 = LDAPGroup(
            dn="cn=users,ou=groups,dc=example,dc=com",
            cn="users",
            description="Standard users",
        )
        group2 = LDAPGroup(
            dn="cn=admins,ou=groups,dc=example,dc=com",
            cn="admins",
            description="Administrators",
        )
        db.session.add(group1)
        db.session.add(group2)
        db.session.commit()

        yield {"config": config, "groups": [group1, group2]}

        db.session.delete(config)
        db.session.delete(group1)
        db.session.delete(group2)
        db.session.commit()


@pytest.fixture
def media_server(app):
    with app.app_context():
        server = MediaServer(
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
        )
        db.session.add(server)
        db.session.commit()
        yield server
        db.session.delete(server)
        db.session.commit()


def test_create_invite_with_ldap_enabled(app, ldap_setup, media_server):
    with app.app_context():
        form_data = {
            "code": "LDAPTEST",
            "expires": "never",
            "server_ids": [str(media_server.id)],
            "create_ldap_user": "true",
        }

        invitation = create_invite(form_data)

        assert invitation is not None
        assert invitation.code == "LDAPTEST"
        assert invitation.create_ldap_user is True

        # Cleanup
        db.session.delete(invitation)
        db.session.commit()


def test_create_invite_without_ldap(app, ldap_setup, media_server):
    with app.app_context():
        form_data = {
            "code": "NOLDAP",
            "expires": "never",
            "server_ids": [str(media_server.id)],
            "create_ldap_user": "",  # Not checked
        }

        invitation = create_invite(form_data)

        assert invitation is not None
        assert invitation.code == "NOLDAP"
        assert invitation.create_ldap_user is False

        # Cleanup
        db.session.delete(invitation)
        db.session.commit()
