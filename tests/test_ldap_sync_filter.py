"""
An optional LDAP sync filter limits the users that sync imports (#1261).

Without it, sync imports every entry of the user object class, service
accounts too. The filter applies only to sync. Login keeps its own filter
(test_ldap_client.py checks this).
"""

from unittest.mock import MagicMock, patch

import pytest

from app.extensions import db
from app.models import LDAPConfiguration
from app.services.ldap.encryption import encrypt_credential
from app.services.ldap.filters import build_sync_filter, is_valid_filter
from app.services.ldap.user_sync import list_ldap_users

GROUP_FILTER = "(memberOf=cn=users,ou=groups,dc=example,dc=com)"
SETTINGS_FORM = {
    "server_url": "ldap://ldap.example.com:389",
    "user_base_dn": "ou=people,dc=example,dc=com",
    "user_search_filter": "(uid={username})",
    "username_attribute": "uid",
    "email_attribute": "mail",
    "user_object_class": "inetOrgPerson",
    "admin_group_dn": "",
}


@pytest.fixture(autouse=True)
def _delete_ldap_config(app):
    """Delete the LDAP configuration after each test.

    The session fixture does not delete it, and the settings route makes one.
    """
    yield
    with app.app_context():
        LDAPConfiguration.query.delete()
        db.session.commit()


@pytest.fixture
def ldap_config(session):
    config = LDAPConfiguration(
        enabled=True,
        server_url="ldap://ldap.example.com:389",
        service_account_dn="cn=wizarr,ou=people,dc=example,dc=com",
        service_account_password_encrypted=encrypt_credential("secret"),
        user_base_dn="ou=people,dc=example,dc=com",
        user_search_filter="(uid={username})",
        user_object_class="inetOrgPerson",
        username_attribute="uid",
        email_attribute="mail",
        user_sync_filter=GROUP_FILTER,
    )
    session.add(config)
    session.commit()
    return config


def test_sync_filter_is_combined_with_object_class():
    assert build_sync_filter("inetOrgPerson", None) == "(objectClass=inetOrgPerson)"
    assert build_sync_filter("inetOrgPerson", "   ") == "(objectClass=inetOrgPerson)"
    assert (
        build_sync_filter("person", f" {GROUP_FILTER} ")
        == f"(&(objectClass=person){GROUP_FILTER})"
    )


@pytest.mark.parametrize(
    ("search_filter", "valid"),
    [
        (GROUP_FILTER, True),
        ("(|(memberOf=cn=a,dc=x)(memberOf=cn=b,dc=x))", True),
        ("(&(objectClass=person)(!(uid=svc-*)))", True),
        ("memberOf=cn=users", False),
        ("(memberOf=cn=users", False),
        ("(uid=a)(uid=b)", False),
        ("()", False),
    ],
)
def test_filter_syntax_check(search_filter, valid):
    assert is_valid_filter(search_filter) is valid


def test_sync_searches_with_the_combined_filter(ldap_config):
    conn = MagicMock()
    conn.search.return_value = True
    conn.entries = []

    with patch("app.services.ldap.user_sync.LDAPClient") as client_class:
        client_class.return_value.service_connection.return_value = conn
        ok, users = list_ldap_users()

    assert ok
    assert users == []
    search_filter = conn.search.call_args.kwargs["search_filter"]
    assert search_filter == f"(&(objectClass=inetOrgPerson){GROUP_FILTER})"


def test_settings_reject_invalid_sync_filter(admin_client):
    form = {**SETTINGS_FORM, "user_sync_filter": "memberOf=cn=users"}

    body = admin_client.post("/settings/ldap", data=form).get_data(as_text=True)

    assert "This LDAP filter is not valid" in body
    assert LDAPConfiguration.query.count() == 0


def test_settings_save_sync_filter(admin_client):
    form = {**SETTINGS_FORM, "user_sync_filter": f"  {GROUP_FILTER}  "}

    admin_client.post("/settings/ldap", data=form)

    config = LDAPConfiguration.query.one()
    assert config.user_sync_filter == GROUP_FILTER

    admin_client.post("/settings/ldap", data={**SETTINGS_FORM, "user_sync_filter": ""})
    db.session.refresh(config)
    assert config.user_sync_filter is None


def test_sync_route_shows_list_error_and_imports_users(admin_client, ldap_config):
    list_users = "app.services.ldap.user_sync.list_ldap_users"
    with patch(list_users, return_value=(False, "Cannot connect to LDAP server")):
        body = admin_client.post("/settings/ldap/users/sync-all").get_data(as_text=True)
    assert "Cannot connect to LDAP server" in body

    found = [{"username": "alice", "email": "", "dn": "uid=alice,dc=example"}]
    with (
        patch(list_users, return_value=(True, found)),
        patch(
            "app.services.ldap.user_sync.import_ldap_user", return_value=(True, "")
        ) as import_user,
    ):
        admin_client.post("/settings/ldap/users/sync-all")
    import_user.assert_called_once_with("alice")
