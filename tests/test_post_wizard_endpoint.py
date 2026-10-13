"""Tests for the /wizard/post-wizard endpoint.

This endpoint shows the post-invite wizard steps after a user accepts an
invitation and creates an account.
"""

import pytest

from app.models import Invitation, MediaServer, WizardStep
from app.services.invite_code_manager import InviteCodeManager


@pytest.fixture
def jellyfin_invite(session):
    """Add a Jellyfin server and the invitation "TEST123" for it."""
    server = MediaServer(
        name="Test Jellyfin",
        server_type="jellyfin",
        url="http://localhost:8096",
        api_key="test_key",
        verified=True,
    )
    invitation = Invitation(code="TEST123", unlimited=True)
    invitation.servers.append(server)
    session.add_all([server, invitation])
    session.commit()
    return invitation


def _add_steps(session, server_type: str, category: str, *markdowns: str) -> None:
    session.add_all(
        WizardStep(
            server_type=server_type,
            category=category,
            position=position,
            markdown=markdown,
        )
        for position, markdown in enumerate(markdowns)
    )
    session.commit()


def _grant_wizard_access(client, code: str = "TEST123", *, invite_code=None) -> None:
    """Put the session in the state that an accepted invitation makes."""
    with client.session_transaction() as sess:
        sess["wizard_access"] = code
        if invite_code:
            sess[InviteCodeManager.STORAGE_KEY] = invite_code


def _assert_invite_data_cleared(client) -> None:
    with client.session_transaction() as sess:
        assert sess.get(InviteCodeManager.STORAGE_KEY) is None
        assert "wizard_access" not in sess


def test_redirect_to_help_page_when_not_authenticated(client, session):
    response = client.get("/wizard/post-wizard", follow_redirects=False)

    # Show the help page, not the admin login.
    assert response.status_code == 302
    assert response.location == "/wizard/help"


def test_only_display_post_invite_steps(client, session, jellyfin_invite):
    _add_steps(session, "jellyfin", "pre_invite", "# Pre-invite step")
    _add_steps(session, "jellyfin", "post_invite", "# Post-invite step")
    _grant_wizard_access(client)

    response = client.get("/wizard/post-wizard")

    assert response.status_code == 200
    assert b"Post-invite step" in response.data
    assert b"Pre-invite step" not in response.data


def test_no_post_invite_steps_completes_and_clears_invite_data(
    client, session, jellyfin_invite
):
    _grant_wizard_access(client, invite_code="TEST123")

    response = client.get("/wizard/post-wizard", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/wizard/complete"

    client.get(response.location)
    _assert_invite_data_cleared(client)


def test_clear_invite_data_after_completing_all_steps(client, session, jellyfin_invite):
    _add_steps(session, "jellyfin", "post_invite", "# Final step")
    _grant_wizard_access(client, invite_code="TEST123")

    # "next" on the last step completes the wizard.
    response = client.get("/wizard/post-wizard/0?dir=next", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/wizard/complete"

    response = client.get("/wizard/complete", follow_redirects=False)
    assert response.status_code == 302
    _assert_invite_data_cleared(client)


def test_fallback_to_first_server_when_no_invitation(client, session):
    session.add(
        MediaServer(
            name="Test Plex",
            server_type="plex",
            url="http://localhost:32400",
            api_key="test_key",
            verified=True,
        )
    )
    _add_steps(session, "plex", "post_invite", "# Plex step")
    # No invitation has this code.
    _grant_wizard_access(client, "INVALID")

    response = client.get("/wizard/post-wizard")

    assert response.status_code == 200
    assert b"Plex step" in response.data


def test_error_when_no_servers_configured(client, session):
    _grant_wizard_access(client)

    response = client.get("/wizard/post-wizard", follow_redirects=False)

    assert response.status_code == 302
    assert response.location == "/"


def test_htmx_next_step_returns_partial_response(client, session, jellyfin_invite):
    """HTMX navigation returns the next step instead of a redirect."""
    _add_steps(session, "jellyfin", "post_invite", "# Step 1", "# Step 2")
    _grant_wizard_access(client)

    initial_response = client.get("/wizard/post-wizard/0")
    assert initial_response.status_code == 200
    assert b"Step 1" in initial_response.data

    response = client.get(
        "/wizard/post-wizard/1",
        query_string={"dir": "next"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.headers.get("X-Wizard-Idx") == "1"
    assert response.headers.get("HX-Redirect") is None
    assert b"Step 2" in response.data
