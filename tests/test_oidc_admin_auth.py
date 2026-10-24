"""Unit tests for OIDC admin-panel authentication."""

import pytest

from app.extensions import db
from app.models import AdminAccount, OIDCConfiguration


@pytest.fixture
def oidc_config_with_group_gate(app):
    """OIDC config that requires a 'groups' claim to contain 'wizarr-admins'."""
    with app.app_context():
        config = OIDCConfiguration(
            enabled=True,
            display_name="TestIdP",
            discovery_url="https://idp.example.com/.well-known/openid-configuration",
            client_id="wizarr",
            client_secret_encrypted=None,
            scopes="openid profile email",
            username_claim="preferred_username",
            admin_claim="groups",
            admin_claim_values="wizarr-admins, admins",
        )
        db.session.add(config)
        db.session.commit()
        yield config
        db.session.delete(config)
        db.session.commit()


@pytest.fixture
def oidc_config_open(app):
    """OIDC config with no admin claim restriction configured."""
    with app.app_context():
        config = OIDCConfiguration(
            enabled=True,
            display_name="TestIdP",
            discovery_url="https://idp.example.com/.well-known/openid-configuration",
            client_id="wizarr",
            scopes="openid profile email",
            username_claim="preferred_username",
        )
        db.session.add(config)
        db.session.commit()
        yield config
        db.session.delete(config)
        db.session.commit()


def test_oidc_login_success_creates_account(app, oidc_config_with_group_gate):
    from app.blueprints.auth.oidc_auth import handle_oidc_login

    with app.app_context():
        userinfo = {
            "sub": "abc123",
            "preferred_username": "marvin",
            "email": "marvin@example.com",
            "groups": ["wizarr-admins", "everyone"],
        }

        success, message = handle_oidc_login(oidc_config_with_group_gate, userinfo)

        assert success is True
        assert message == "Login successful"

        admin = AdminAccount.query.filter_by(username="marvin").first()
        assert admin is not None
        assert admin.auth_source == "oidc"
        assert admin.external_id == "abc123"
        assert admin.password_hash is None

        db.session.delete(admin)
        db.session.commit()


def test_oidc_login_denied_without_required_group(app, oidc_config_with_group_gate):
    from app.blueprints.auth.oidc_auth import handle_oidc_login

    with app.app_context():
        userinfo = {
            "sub": "def456",
            "preferred_username": "regular_user",
            "groups": ["everyone"],
        }

        success, message = handle_oidc_login(oidc_config_with_group_gate, userinfo)

        assert success is False
        assert "not authorized as an administrator" in message
        assert AdminAccount.query.filter_by(username="regular_user").first() is None


def test_oidc_login_denied_missing_sub(app, oidc_config_with_group_gate):
    from app.blueprints.auth.oidc_auth import handle_oidc_login

    with app.app_context():
        success, message = handle_oidc_login(
            oidc_config_with_group_gate, {"preferred_username": "no_sub"}
        )

        assert success is False
        assert "subject identifier" in message


def test_oidc_login_open_config_allows_any_authenticated_user(app, oidc_config_open):
    """When no admin_claim is configured, any authenticated identity is
    admitted -- this is documented (loudly) in the settings UI."""
    from app.blueprints.auth.oidc_auth import handle_oidc_login

    with app.app_context():
        success, message = handle_oidc_login(
            oidc_config_open, {"sub": "xyz", "preferred_username": "anyone"}
        )

        assert success is True

        admin = AdminAccount.query.filter_by(username="anyone").first()
        assert admin is not None

        db.session.delete(admin)
        db.session.commit()


def test_oidc_login_links_existing_local_admin_by_username(
    app, oidc_config_with_group_gate
):
    """An existing local (or LDAP) admin account with a matching username
    can be authenticated via OIDC without creating a duplicate account."""
    from app.blueprints.auth.oidc_auth import handle_oidc_login

    with app.app_context():
        existing = AdminAccount(username="shared_user")
        existing.set_password("localpass123")
        db.session.add(existing)
        db.session.commit()
        existing_id = existing.id

        userinfo = {
            "sub": "sso-sub-789",
            "preferred_username": "shared_user",
            "groups": ["wizarr-admins"],
        }

        success, _message = handle_oidc_login(oidc_config_with_group_gate, userinfo)

        assert success is True
        assert AdminAccount.query.filter_by(username="shared_user").count() == 1

        admin = db.session.get(AdminAccount, existing_id)
        assert admin.external_id == "sso-sub-789"
        assert admin.auth_source == "oidc"

        db.session.delete(admin)
        db.session.commit()


def test_oidc_login_disabled_config_not_used_by_client_helper(app):
    """get_oidc_client() must fail closed when OIDC isn't configured."""
    from app.services.oidc.client import get_oidc_client

    with app.app_context():
        assert OIDCConfiguration.query.first() is None
        assert get_oidc_client() is None
