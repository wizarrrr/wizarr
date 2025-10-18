import pytest
from sqlalchemy import text

from app.extensions import db
from app.models import Invitation, MediaServer, WizardStep
from app.services.invite_code_manager import InviteCodeManager


@pytest.fixture
def session(app):
    """Provide a clean database session for wizard flow tests."""
    with app.app_context():
        db.session.rollback()
        db.session.execute(text("DELETE FROM invitation_server"))
        db.session.query(WizardStep).delete()
        db.session.query(Invitation).delete()
        db.session.query(MediaServer).delete()
        db.session.commit()

        yield db.session

        db.session.rollback()


def _setup_invitation(
    session, *, code: str, server_type: str = "plex", steps: list[str]
):
    """Create a media server, invitation, and associated pre-invite steps."""
    server = MediaServer(
        name=f"{server_type.title()} Server",
        server_type=server_type,
        url=f"http://{server_type}.example.com",
        api_key=f"{server_type}_key",
    )
    session.add(server)
    session.flush()

    invitation = Invitation(code=code, unlimited=True, used=False)
    invitation.servers.append(server)
    session.add(invitation)
    session.flush()

    for position, content in enumerate(steps):
        session.add(
            WizardStep(
                server_type=server_type,
                category="pre_invite",
                position=position,
                markdown=f"# Step {position + 1}\n\n{content}",
            )
        )

    session.commit()


class TestPreWizardFlow:
    def test_single_step_shows_continue_button(self, app, client, session):
        """Single pre-invite step should render a Continue button linking to join page."""
        _setup_invitation(session, code="SINGLE123", steps=["Only step content"])

        with client.session_transaction() as sess:
            sess[InviteCodeManager.STORAGE_KEY] = "SINGLE123"
            sess["invitation_in_progress"] = True

        response = client.get("/wizard/pre-wizard")
        assert response.status_code == 200
        body = response.data.decode()

        # Desktop button should use full navigation to the completion route
        anchor_id = 'id="wizard-next-btn-desktop"'
        assert anchor_id in body
        snippet = body[body.index(anchor_id) : body.index(anchor_id) + 460]
        assert "Continue to Invite" in snippet
        assert 'href="/wizard/pre-wizard/complete"' in snippet
        assert 'hx-get="/wizard/pre-wizard/complete"' in snippet
        assert "hx-vals" not in snippet

        # Trigger completion route and ensure session flag is set
        complete_resp = client.get(
            "/wizard/pre-wizard/complete", follow_redirects=False
        )
        assert complete_resp.status_code == 302
        assert complete_resp.location.endswith("/j/SINGLE123")

        with client.session_transaction() as sess:
            assert sess.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY) is True

    def test_multi_step_htmx_progression_renders_each_step(self, app, client, session):
        """HTMX navigation should deliver each step sequentially without embedding invite page."""
        _setup_invitation(
            session,
            code="MULTI456",
            steps=["First pre-step", "Second pre-step"],
        )

        with client.session_transaction() as sess:
            sess[InviteCodeManager.STORAGE_KEY] = "MULTI456"
            sess["invitation_in_progress"] = True

        initial = client.get("/wizard/pre-wizard")
        assert initial.status_code == 200
        assert b"First pre-step" in initial.data

        # Simulate HTMX "next" request for the second step
        htmx_response = client.get(
            "/wizard/pre-wizard/1",
            query_string={"dir": "next"},
            headers={"HX-Request": "true"},
        )
        assert htmx_response.status_code == 200
        assert b"Second pre-step" in htmx_response.data
        assert htmx_response.headers.get("X-Wizard-Idx") == "1"

        # Loading the final step directly should expose the Continue button
        final_page = client.get("/wizard/pre-wizard/1")
        assert final_page.status_code == 200
        final_body = final_page.data.decode()
        anchor_id = 'id="wizard-next-btn-desktop"'
        assert anchor_id in final_body
        snippet = final_body[
            final_body.index(anchor_id) : final_body.index(anchor_id) + 460
        ]
        assert "Continue to Invite" in snippet
        assert 'href="/wizard/pre-wizard/complete"' in snippet
        assert 'hx-get="/wizard/pre-wizard/complete"' in snippet
        assert "hx-vals" not in snippet

    def test_invite_route_resets_pre_wizard_flag(self, app, client, session):
        """Invite route must clear stale completion flag and redirect back to pre-wizard."""
        code = "RESET789"
        _setup_invitation(session, code=code, steps=["Reset flow step"])

        with client.session_transaction() as sess:
            sess[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] = True

        response = client.get(f"/j/{code}", follow_redirects=False)
        assert response.status_code == 302
        assert response.location.endswith("/wizard/pre-wizard")

        with client.session_transaction() as sess:
            assert sess.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY, False) is False

    def test_pre_wizard_complete_sets_hx_redirect(self, app, client, session):
        """Completion endpoint should force full-page redirects for HTMX triggers."""
        code = "HXRED321"
        _setup_invitation(session, code=code, steps=["Only"])

        with client.session_transaction() as sess:
            sess[InviteCodeManager.STORAGE_KEY] = code
            sess["invitation_in_progress"] = True

        response = client.get(
            "/wizard/pre-wizard/complete",
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )

        assert response.status_code == 204
        assert response.headers.get("HX-Redirect") == f"/j/{code}"
