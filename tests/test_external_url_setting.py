"""Tests for the "Public Wizarr URL" setting.

Invite and password-reset links are built from whatever URL the admin's
browser happens to show (`HX-Current-URL` / `request.url_root`), which
breaks the moment an admin manages Wizarr from an address the recipient
can't reach (a LAN IP, a VPN hostname, `localhost`, etc. -- see
https://github.com/wizarrrr/wizarr/issues/244). Setting a "Public Wizarr
URL" in General settings should override that guess everywhere a link is
generated, independent of how the admin is currently connected.
"""

from werkzeug.datastructures import MultiDict

from app.blueprints.api.api_routes import _generate_invitation_url
from app.forms.general import GeneralSettingsForm
from app.models import AdminAccount, MediaServer, Settings, User
from app.services.instance_url_resolver import (
    get_configured_public_url,
    resolve_base_url,
)

# /invite is an HTMX-only endpoint (it redirects to the dashboard otherwise).
HX = {"HX-Request": "true", "HX-Current-URL": "http://192.168.1.50:5690/admin/invites"}


def _login(client, session, username="testadmin"):
    admin = AdminAccount(username=username)
    admin.set_password("TestPass123")
    session.add(admin)
    session.commit()
    resp = client.post("/login", data={"username": username, "password": "TestPass123"})
    assert resp.status_code in {200, 302, 303}
    return admin


def _server(session):
    server = MediaServer(
        name="Plex", server_type="plex", url="http://plex.local", api_key="token"
    )
    session.add(server)
    session.commit()
    return server


class TestInstanceUrlResolverUnit:
    """Unit tests for app.services.instance_url_resolver.

    Uses the `session` fixture (not a bare `db.session`) so the Settings
    table is reset between tests -- these all write a `public_url` row and
    the `app` fixture is session-scoped, so state would otherwise leak
    across tests and collide on the unique `key` column.
    """

    def test_get_configured_public_url_unset(self, session):
        assert get_configured_public_url() is None

    def test_get_configured_public_url_blank_is_none(self, session):
        session.add(Settings(key="public_url", value="   "))
        session.commit()
        assert get_configured_public_url() is None

    def test_get_configured_public_url_normalizes_trailing_slash(self, session):
        session.add(Settings(key="public_url", value=" https://invites.example.com/ "))
        session.commit()
        assert get_configured_public_url() == "https://invites.example.com"

    def test_resolve_base_url_prefers_configured_setting(self, app, session):
        session.add(Settings(key="public_url", value="https://invites.example.com"))
        session.commit()
        with app.test_request_context(
            "/invite",
            headers={"HX-Current-URL": "http://192.168.1.50:5690/admin/invites"},
        ):
            assert resolve_base_url() == "https://invites.example.com"

    def test_resolve_base_url_falls_back_to_hx_current_url(self, app, session):
        with app.test_request_context(
            "/invite",
            headers={"HX-Current-URL": "http://192.168.1.50:5690/admin/invites"},
        ):
            assert resolve_base_url() == "http://192.168.1.50:5690"

    def test_resolve_base_url_falls_back_to_request_root(self, app, session):
        with app.test_request_context(
            "/reset-password-modal", base_url="http://10.0.0.5:5690"
        ):
            assert resolve_base_url() == "http://10.0.0.5:5690"


class TestInviteLinkUsesConfiguredUrl:
    """Integration: invite creation honors the configured Public Wizarr URL."""

    def test_invite_link_falls_back_to_hx_current_url_when_unset(self, client, session):
        """Regression: unset setting keeps the historical auto-detect behavior."""
        _login(client, session)
        server = _server(session)

        resp = client.post(
            "/invite",
            data={"server_ids": str(server.id), "expires": "never"},
            headers=HX,
        )
        assert resp.status_code == 200
        assert b"http://192.168.1.50:5690/j/" in resp.data

    def test_invite_link_uses_configured_url_over_browser_url(self, client, session):
        """The configured URL wins even though the admin is on a different host."""
        _login(client, session)
        server = _server(session)
        session.add(Settings(key="public_url", value="https://invites.example.com"))
        session.commit()

        resp = client.post(
            "/invite",
            data={"server_ids": str(server.id), "expires": "never"},
            headers=HX,
        )
        assert resp.status_code == 200
        assert b"https://invites.example.com/j/" in resp.data
        assert b"192.168.1.50" not in resp.data


class TestPasswordResetLinkUsesConfiguredUrl:
    """Integration: password-reset links honor the configured Public Wizarr URL."""

    def _user(self, session, server):
        user = User(
            username="reset-target",
            email="reset-target@example.com",
            token="test-token",
            code="INVITE123",
            server_id=server.id,
        )
        session.add(user)
        session.commit()
        return user

    def test_generate_reset_link_uses_configured_url(self, client, session):
        _login(client, session, username="reset_admin")
        server = _server(session)
        user = self._user(session, server)
        session.add(Settings(key="public_url", value="https://invites.example.com"))
        session.commit()

        resp = client.post(f"/users/{user.id}/generate-reset-link")
        assert resp.status_code == 200
        assert b"https://invites.example.com/reset/" in resp.data


class TestApiInvitationUrlUsesConfiguredUrl:
    """The API's invitation URL builder returns an absolute URL when configured."""

    def test_relative_path_when_unset(self, app, session):
        with app.test_request_context("/api/invitations"):
            assert _generate_invitation_url("ABC123") == "/j/ABC123"

    def test_absolute_url_when_configured(self, app, session):
        session.add(Settings(key="public_url", value="https://invites.example.com"))
        session.commit()
        with app.test_request_context("/api/invitations"):
            assert (
                _generate_invitation_url("ABC123")
                == "https://invites.example.com/j/ABC123"
            )


def _submit(app, public_url):
    """Build the form the way a real POST would: via `formdata`, so the
    Optional() validator sees the field as actually submitted (WTForms only
    checks `raw_data`, which a `data=` kwarg alone leaves empty)."""
    with app.app_context(), app.test_request_context():
        form = GeneralSettingsForm(
            formdata=MultiDict(
                {
                    "server_name": "Wizarr",
                    "public_url": public_url,
                    "expiry_action": "delete",
                }
            ),
            meta={"csrf": False},
        )
        form.validate()
        return form


class TestGeneralSettingsFormValidation:
    """The new field should accept home-lab-style hosts and reject garbage."""

    def test_accepts_bare_local_hostname(self, app):
        form = _submit(app, "http://wizarr:5690")
        assert "public_url" not in form.errors

    def test_accepts_dotted_lan_domain(self, app):
        form = _submit(app, "https://invites.diaz.lan")
        assert "public_url" not in form.errors

    def test_blank_is_valid(self, app):
        form = _submit(app, "")
        assert "public_url" not in form.errors

    def test_rejects_non_url_garbage(self, app):
        form = _submit(app, "not a url")
        assert "public_url" in form.errors


class TestGeneralSettingsRouteSavesAndLoadsPublicUrl:
    """End-to-end: saving General settings persists public_url distinctly
    from the per-media-server "external_url" field, and reloads it."""

    def test_save_and_reload(self, client, session):
        _login(client, session, username="general_settings_admin")

        resp = client.post(
            "/settings/general",
            data={
                "server_name": "My Wizarr",
                "public_url": "https://invites.example.com",
                "expiry_action": "delete",
            },
            headers={"HX-Request": "true"},
        )
        assert resp.status_code == 200

        setting = Settings.query.filter_by(key="public_url").first()
        assert setting is not None
        assert setting.value == "https://invites.example.com"

        # Reloading the form should show the saved value.
        resp = client.get("/settings/general", headers={"HX-Request": "true"})
        assert b"https://invites.example.com" in resp.data

    def test_does_not_collide_with_per_server_external_url(self, client, session):
        """public_url (global) and MediaServer.external_url (per-server) are
        stored under different Settings keys and must not clobber each other."""
        server = _server(session)
        server.external_url = "https://jellyfin.example.com"
        session.commit()
        session.add(Settings(key="external_url", value="https://jellyfin.example.com"))
        session.add(Settings(key="public_url", value="https://invites.example.com"))
        session.commit()

        assert (
            Settings.query.filter_by(key="external_url").first().value
            == "https://jellyfin.example.com"
        )
        assert (
            Settings.query.filter_by(key="public_url").first().value
            == "https://invites.example.com"
        )
