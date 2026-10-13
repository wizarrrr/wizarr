"""Error handling tests for the wizard routes.

Tests cover:
- Invalid and expired invite codes
- Invite codes that expire during the wizard
- Database errors (the routes fall back and do not show a 500 error)
- Steps that are missing or that cannot render
"""

import datetime
from datetime import timedelta
from unittest.mock import patch

import pytest

from app.models import Invitation, MediaServer, WizardStep
from app.services.invite_code_manager import InviteCodeManager


def _utc_now() -> datetime.datetime:
    """Return the time in UTC without a time zone, as Wizarr stores it."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def _add_invitation(session, code: str, *, with_server: bool = True, **fields):
    """Add an invitation for a Jellyfin server."""
    invitation = Invitation(code=code, **({"unlimited": True} | fields))
    if with_server:
        server = MediaServer(
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test-key",
        )
        session.add(server)
        invitation.servers.append(server)
    session.add(invitation)
    session.commit()
    return invitation


def _add_pre_invite_step(session, markdown: str = "# Read first") -> None:
    session.add(
        WizardStep(
            server_type="jellyfin",
            category="pre_invite",
            position=0,
            markdown=markdown,
        )
    )
    session.commit()


def _start_invite_session(client, code: str) -> None:
    """Put the session in the state that the /j/<code> route makes."""
    with client.session_transaction() as sess:
        sess[InviteCodeManager.STORAGE_KEY] = code
        sess["invitation_in_progress"] = True


def _flashes(client) -> list[str]:
    with client.session_transaction() as sess:
        return [message for _category, message in sess.get("_flashes", [])]


class TestInvalidInviteCodeHandling:
    def test_pre_wizard_with_no_invite_code(self, client, session):
        """Test pre-wizard redirects to the help page with no invite code."""
        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        assert response.location == "/wizard/help"

    def test_pre_wizard_with_invalid_invite_code(self, client, session):
        """Test pre-wizard redirects to home with invalid invite code."""
        with client.session_transaction() as sess:
            sess[InviteCodeManager.STORAGE_KEY] = "INVALID123"

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        assert response.location == "/"

    @pytest.mark.parametrize(
        "fields",
        [
            {"expires": _utc_now() - timedelta(hours=1)},
            {"unlimited": False, "used": True},
        ],
        ids=["expired", "used"],
    )
    def test_pre_wizard_rejects_unusable_invitation(self, client, session, fields):
        _add_invitation(session, "BADINV123", **fields)
        with client.session_transaction() as sess:
            sess[InviteCodeManager.STORAGE_KEY] = "BADINV123"

        response = client.get("/wizard/pre-wizard", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/"
        with client.session_transaction() as sess:
            assert InviteCodeManager.STORAGE_KEY not in sess


class TestSessionExpirationHandling:
    def test_pre_wizard_validates_invite_code_on_each_request(self, client, session):
        invitation = _add_invitation(
            session, "VALID123", expires=_utc_now() + timedelta(days=7)
        )
        _add_pre_invite_step(session)
        _start_invite_session(client, "VALID123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 200
        assert b"Read first" in response.data

        # The invitation expires while the user is in the wizard.
        invitation.expires = _utc_now() - timedelta(hours=1)
        session.commit()

        response = client.get("/wizard/pre-wizard", follow_redirects=False)
        assert response.status_code == 302
        assert response.location == "/"


class TestDatabaseErrorHandling:
    def test_pre_wizard_database_error_loading_steps_opens_join_page(
        self, client, session, caplog
    ):
        _add_invitation(session, "VALID123")
        _add_pre_invite_step(session)
        _start_invite_session(client, "VALID123")

        with patch("app.blueprints.wizard.routes.WizardStep") as mock_wizard_step:
            mock_wizard_step.query.filter_by.side_effect = Exception("Database error")
            response = client.get("/wizard/pre-wizard", follow_redirects=False)

        assert mock_wizard_step.query.filter_by.called
        assert "Database error querying wizard steps" in caplog.text
        # Without steps, the user continues to the join page.
        assert response.status_code == 302
        assert response.location == "/j/VALID123"
        with client.session_transaction() as sess:
            assert sess[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] is True

    def test_post_wizard_handles_database_error_loading_invitation(
        self, client, session
    ):
        session.add(
            MediaServer(
                name="Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test-key",
            )
        )
        session.commit()
        with client.session_transaction() as sess:
            sess["wizard_access"] = "TESTCODE123"

        with patch("app.blueprints.wizard.routes.Invitation") as mock_invitation:
            mock_invitation.query.filter_by.side_effect = Exception("Database error")
            response = client.get("/wizard/post-wizard", follow_redirects=False)

        mock_invitation.query.filter_by.assert_called_once_with(code="TESTCODE123")
        # The route falls back to the first server. It has no post-invite steps.
        assert response.status_code == 302
        assert response.location == "/wizard/complete"


class TestGracefulDegradation:
    def test_pre_wizard_with_no_servers_configured(self, client, session):
        _add_invitation(session, "NOSERVER123", with_server=False)
        _start_invite_session(client, "NOSERVER123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/"
        assert any("No media servers are configured" in m for m in _flashes(client))

    def test_pre_wizard_with_no_pre_invite_steps(self, client, session):
        _add_invitation(session, "NOSTEPS123")
        _start_invite_session(client, "NOSTEPS123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/j/NOSTEPS123"
        with client.session_transaction() as sess:
            assert sess[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] is True

    def test_wizard_handles_broken_step_content(self, client, session):
        _add_invitation(session, "BROKEN123")
        _add_pre_invite_step(
            session, "# Test\n{{ undefined_variable.nonexistent_method() }}"
        )
        _start_invite_session(client, "BROKEN123")

        response = client.get("/wizard/pre-wizard", follow_redirects=False)

        assert response.status_code == 200
        assert b"Error Loading Step" in response.data


class TestComboWizardErrors:
    def test_combo_wizard_without_server_order(self, client, session):
        _start_invite_session(client, "COMBO123")

        response = client.get("/wizard/combo/pre_invite/0", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/wizard/"

    def test_combo_wizard_handles_database_error_loading_steps(self, client, session):
        _start_invite_session(client, "COMBO123")
        with client.session_transaction() as sess:
            sess["wizard_server_order"] = ["jellyfin", "plex"]

        with patch("app.blueprints.wizard.routes._steps") as mock_steps:
            mock_steps.side_effect = Exception("Database error")
            response = client.get("/wizard/combo/pre_invite/0", follow_redirects=False)

        assert mock_steps.call_count == 2
        # Without steps, the user continues to the join page.
        assert response.status_code == 302
        assert response.location == "/j/COMBO123"


class TestBundleWizardErrors:
    def test_bundle_wizard_without_bundle_id(self, client, session):
        _start_invite_session(client, "BUNDLE123")

        response = client.get("/wizard/bundle/0", follow_redirects=False)

        assert response.status_code == 302
        assert response.location == "/wizard/"

    def test_bundle_wizard_with_nonexistent_bundle(self, client, session):
        _start_invite_session(client, "BUNDLE123")
        with client.session_transaction() as sess:
            sess["wizard_bundle_id"] = 99999

        response = client.get("/wizard/bundle/0", follow_redirects=False)

        assert response.status_code == 404
