"""Tests for the wizard help page (#997).

Visitors without wizard access see a help page, not the admin login.
"""

from app.models import MediaServer, Settings
from app.services.wizard_access import WizardGuide, public_wizard_guides


def _add_server(session, name: str, server_type: str) -> MediaServer:
    server = MediaServer(name=name, server_type=server_type, url="http://media")
    session.add(server)
    session.commit()
    return server


def _make_wizard_public(session) -> None:
    session.add(Settings(key="wizard_acl_enabled", value="false"))
    session.commit()


def test_wizard_start_without_session_shows_help_page(client, session):
    _add_server(session, "Family Jellyfin", "jellyfin")

    response = client.get("/wizard/", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == "/wizard/help"
    html = response.get_data(as_text=True)
    assert "This page is for invited users" in html
    # Protected wizard steps stay hidden.
    assert "/wizard/jellyfin/0" not in html
    assert "Family Jellyfin" not in html


def test_protected_wizard_step_redirects_to_help_page(client, session):
    _add_server(session, "Family Jellyfin", "jellyfin")

    response = client.get("/wizard/jellyfin/0", follow_redirects=False)

    assert response.status_code == 302
    assert response.location == "/wizard/help"


def test_help_page_links_to_steps_when_wizard_is_public(client, session):
    _add_server(session, "Family Jellyfin", "jellyfin")
    _make_wizard_public(session)

    response = client.get("/wizard/", follow_redirects=True)

    assert response.request.path == "/wizard/help"
    html = response.get_data(as_text=True)
    assert 'href="/wizard/jellyfin/0"' in html
    assert "Open the setup guide for Family Jellyfin" in html


def test_help_page_never_redirects(client, session):
    response = client.get("/wizard/help", follow_redirects=False)

    assert response.status_code == 200


def test_public_wizard_guides_give_one_guide_per_server_type(app, session):
    _add_server(session, "Main Plex", "plex")
    _add_server(session, "Second Plex", "plex")
    _add_server(session, "Books", "audiobookshelf")

    assert public_wizard_guides() == []

    _make_wizard_public(session)

    assert public_wizard_guides() == [
        WizardGuide("Main Plex", "plex"),
        WizardGuide("Books", "audiobookshelf"),
    ]
