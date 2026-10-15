import datetime

import pytest

from app.models import (
    Invitation,
    MediaServer,
    WizardBundle,
    WizardBundleStep,
    WizardStep,
)
from app.services.invite_code_manager import InviteCodeManager

# Only the join form for form-based servers (for example Jellyfin) has this button.
JOIN_FORM = 'id="accept-invite-btn"'


def _add_server(session, server_type: str) -> MediaServer:
    server = MediaServer(
        name=f"{server_type.title()} Server",
        server_type=server_type,
        url=f"http://{server_type}.example.com",
        api_key=f"{server_type}_key",
    )
    session.add(server)
    session.flush()
    return server


def _add_steps(session, server_type: str, category: str, contents: list[str]):
    for position, content in enumerate(contents):
        session.add(
            WizardStep(
                server_type=server_type,
                category=category,
                position=position,
                markdown=f"# Step {position + 1}\n\n{content}",
            )
        )


def _setup_invitation(
    session,
    *,
    code: str,
    server_type: str = "plex",
    steps: list[str],
    post_steps: list[str] | None = None,
    **invitation_fields,
):
    """Create a media server, an invitation, and its pre-invite steps."""
    server = _add_server(session, server_type)

    fields = {"unlimited": True, "used": False} | invitation_fields
    invitation = Invitation(code=code, **fields)
    invitation.servers.append(server)
    session.add(invitation)

    _add_steps(session, server_type, "pre_invite", steps)
    _add_steps(session, server_type, "post_invite", post_steps or [])
    session.commit()


def _start_invite_session(client, code: str) -> None:
    """Put the session in the state that the /j/<code> route makes."""
    with client.session_transaction() as sess:
        sess[InviteCodeManager.STORAGE_KEY] = code
        sess["invitation_in_progress"] = True


def _assert_continue_button(body: str) -> None:
    """Check that the desktop "next" button opens the completion route."""
    anchor_id = 'id="wizard-next-btn-desktop"'
    assert anchor_id in body
    start = body.index(anchor_id)
    snippet = body[start : start + 460]
    assert "Continue to Invite" in snippet
    assert 'href="/wizard/pre-wizard/complete"' in snippet
    assert 'hx-get="/wizard/pre-wizard/complete"' in snippet
    assert "hx-vals" not in snippet


class TestPreWizardFlow:
    def test_single_step_shows_continue_button(self, client, session):
        """Single pre-invite step should render a Continue button linking to join page."""
        _setup_invitation(session, code="SINGLE123", steps=["Only step content"])
        _start_invite_session(client, "SINGLE123")

        response = client.get("/wizard/pre-wizard")
        assert response.status_code == 200
        _assert_continue_button(response.data.decode())

        # Trigger completion route and ensure session flag is set
        complete_resp = client.get(
            "/wizard/pre-wizard/complete", follow_redirects=False
        )
        assert complete_resp.status_code == 302
        assert complete_resp.location.endswith("/j/SINGLE123")

        with client.session_transaction() as sess:
            assert sess.get(InviteCodeManager.PRE_WIZARD_COMPLETE_KEY) is True

    def test_multi_step_htmx_progression_renders_each_step(self, client, session):
        """HTMX navigation should deliver each step sequentially without embedding invite page."""
        _setup_invitation(
            session,
            code="MULTI456",
            steps=["First pre-step", "Second pre-step"],
        )
        _start_invite_session(client, "MULTI456")

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
        _assert_continue_button(final_page.data.decode())

    def test_invite_route_resets_pre_wizard_flag(self, client, session):
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

    def test_pre_wizard_complete_sets_hx_redirect(self, client, session):
        """Completion endpoint should force full-page redirects for HTMX triggers."""
        code = "HXRED321"
        _setup_invitation(session, code=code, steps=["Only"])
        _start_invite_session(client, code)

        response = client.get(
            "/wizard/pre-wizard/complete",
            headers={"HX-Request": "true"},
            follow_redirects=False,
        )

        assert response.status_code == 204
        assert response.headers.get("HX-Redirect") == f"/j/{code}"


class TestInviteLink:
    @pytest.mark.parametrize("server_type", ["plex", "jellyfin", "emby"])
    def test_invite_link_with_pre_steps_opens_pre_wizard(
        self, client, session, server_type
    ):
        _setup_invitation(
            session, code="PRE12345", server_type=server_type, steps=["Read first"]
        )

        response = client.get("/j/PRE12345")
        assert response.status_code == 302
        assert response.location == "/wizard/pre-wizard"

        # The session from the invite link is enough to open the pre-wizard.
        response = client.get("/wizard/pre-wizard")
        assert response.status_code == 200
        assert b"Read first" in response.data

    def test_join_form_shown_after_pre_wizard_complete(self, client, session):
        _setup_invitation(
            session, code="FLOW123", server_type="jellyfin", steps=["Read first"]
        )
        assert client.get("/j/FLOW123").location == "/wizard/pre-wizard"

        with client.session_transaction() as sess:
            sess[InviteCodeManager.PRE_WIZARD_COMPLETE_KEY] = True

        response = client.get("/j/FLOW123")
        assert response.status_code == 200
        assert JOIN_FORM in response.get_data(as_text=True)

    def test_join_form_shown_without_pre_invite_steps(self, client, session):
        _setup_invitation(
            session,
            code="NOPRE123",
            server_type="jellyfin",
            steps=[],
            post_steps=["After you join"],
        )

        response = client.get("/j/NOPRE123")
        assert response.status_code == 200
        assert JOIN_FORM in response.get_data(as_text=True)

    @pytest.mark.parametrize(
        ("code", "invitation_fields", "error"),
        [
            (
                "EXPIRED123",
                {
                    "expires": datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
                    - datetime.timedelta(days=1)
                },
                "Invitation has expired.",
            ),
            (
                "USED123",
                {"unlimited": False, "used": True},
                "Invitation has already been used.",
            ),
            ("UNKNOWN99", None, "Invalid code"),
        ],
        ids=["expired", "used", "unknown"],
    )
    def test_unusable_invite_shows_error_not_join_form(
        self, client, session, code, invitation_fields, error
    ):
        # The pre-invite step makes sure that the check happens before the
        # redirect to the pre-wizard.
        if invitation_fields is not None:
            _setup_invitation(
                session,
                code=code,
                server_type="jellyfin",
                steps=["Read first"],
                **invitation_fields,
            )

        response = client.get(f"/j/{code}")

        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert error in body
        assert JOIN_FORM not in body

    def test_multi_server_invite_shows_steps_of_each_server(self, client, session):
        jellyfin = _add_server(session, "jellyfin")
        emby = _add_server(session, "emby")
        invitation = Invitation(code="COMBO123", unlimited=True, used=False)
        invitation.servers.extend([jellyfin, emby])
        session.add(invitation)
        _add_steps(session, "jellyfin", "pre_invite", ["Jellyfin first"])
        _add_steps(session, "emby", "pre_invite", ["Emby first"])
        session.commit()

        assert client.get("/j/COMBO123").location == "/wizard/pre-wizard"
        response = client.get("/wizard/pre-wizard")
        assert response.status_code == 302
        assert response.location == "/wizard/combo/pre_invite"

        first = client.get("/wizard/combo/pre_invite/0", headers={"HX-Request": "true"})
        assert first.status_code == 200
        assert b"Jellyfin first" in first.data
        assert first.headers["X-Current-Server-Type"] == "jellyfin"

        second = client.get(
            "/wizard/combo/pre_invite/1", headers={"HX-Request": "true"}
        )
        assert second.status_code == 200
        assert b"Emby first" in second.data
        assert second.headers["X-Current-Server-Type"] == "emby"

    def test_bundle_invite_shows_only_pre_invite_bundle_steps(self, client, session):
        server = _add_server(session, "jellyfin")
        pre = WizardStep(
            server_type="jellyfin", category="pre_invite", position=0, markdown="Pre A"
        )
        post = WizardStep(
            server_type="jellyfin",
            category="post_invite",
            position=0,
            markdown="Post A",
        )
        pre2 = WizardStep(
            server_type="jellyfin", category="pre_invite", position=1, markdown="Pre B"
        )
        bundle = WizardBundle(name="Mixed bundle")
        session.add_all([pre, post, pre2, bundle])
        session.flush()
        for position, step in enumerate([pre, post, pre2]):
            session.add(
                WizardBundleStep(
                    bundle_id=bundle.id, step_id=step.id, position=position
                )
            )
        invitation = Invitation(
            code="BUNDLE123", unlimited=True, used=False, wizard_bundle_id=bundle.id
        )
        invitation.servers.append(server)
        session.add(invitation)
        session.commit()

        response = client.get("/j/BUNDLE123")
        assert response.status_code == 302
        assert response.location == "/wizard/bundle/0"

        first = client.get("/wizard/bundle/0")
        assert first.status_code == 200
        assert b"Pre A" in first.data
        second = client.get("/wizard/bundle/1")
        assert second.status_code == 200
        assert b"Pre B" in second.data
        assert b"Post A" not in first.data + second.data
