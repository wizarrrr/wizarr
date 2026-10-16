"""The invite page /j/<code> shows the name of the server the invite is for."""

import pytest

from app.models import Invitation, MediaServer


def _server(session, name):
    server = MediaServer(
        name=name,
        server_type="jellyfin",
        url="http://localhost:8096",
        api_key="test_api_key",
        verified=True,
    )
    session.add(server)
    session.flush()
    return server


@pytest.fixture
def invitation(session):
    """Return a factory that adds an invitation with the code CODE12345."""

    def make(servers=(), server=None):
        invitation = Invitation(
            code="CODE12345",
            used=False,
            unlimited=False,
            duration="unlimited",
            server=server,
        )
        invitation.servers.extend(servers)
        session.add(invitation)
        session.commit()

    return make


def _invite_page(client):
    response = client.get("/j/CODE12345")
    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_invitation_page_displays_server_name(client, session, invitation):
    invitation(servers=[_server(session, "My Jellyfin Server")])

    html = _invite_page(client)

    assert "You've been invited to join the My Jellyfin Server server!" in html


def test_invitation_with_no_server_association_falls_back(client, session, invitation):
    """An invite with no server uses the first server in the database."""
    _server(session, "Default Server")
    invitation()

    html = _invite_page(client)

    assert "Create Account" in html
    assert "You've been invited to join the Default Server server!" in html


def test_invitation_with_legacy_server_field(client, session, invitation):
    invitation(server=_server(session, "Legacy Server"))

    assert "Legacy Server" in _invite_page(client)


def test_invitation_with_both_server_associations(client, session, invitation):
    """The many-to-many servers take precedence over the legacy server field."""
    invitation(
        servers=[_server(session, "New Server")],
        server=_server(session, "Legacy Server"),
    )

    html = _invite_page(client)

    assert "New Server" in html
    assert "Legacy Server" not in html
