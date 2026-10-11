"""The LDAP sync matches a Wizarr user without case (#1350).

Wizarr writes LDAP uids in lowercase. A user invited as "JohnDoe" gets the
LDAP uid "johndoe". The sync must find the "JohnDoe" user and must not
import a second user.
"""

from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import LDAPConfiguration, User
from app.tasks.ldap_sync import sync_ldap_users


@pytest.fixture
def ldap_enabled(session):
    config = LDAPConfiguration(
        enabled=True,
        server_url="ldap://ldap.example.com:389",
        user_base_dn="ou=people,dc=example,dc=com",
    )
    session.add(config)
    session.commit()
    yield config
    db.session.delete(config)
    db.session.commit()


def test_sync_does_not_import_a_user_that_differs_only_in_case(
    app, session, ldap_enabled
):
    session.add(User(username="JohnDoe", email="john@example.com", token="t", code="c"))
    session.commit()
    ldap_user = {
        "username": "johndoe",
        "email": "john@example.com",
        "dn": "uid=johndoe,ou=people,dc=example,dc=com",
    }

    with (
        patch(
            "app.services.ldap.user_sync.list_ldap_users",
            return_value=(True, [ldap_user]),
        ),
        patch("app.services.ldap.user_sync.LDAPClient") as ldap_client,
    ):
        sync_ldap_users(app)

    assert [u.username for u in User.query.all()] == ["JohnDoe"]
    ldap_client.assert_not_called()
