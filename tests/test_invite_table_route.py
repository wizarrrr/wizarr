"""The /invite/table route compares expiry dates without a TypeError.

SQLite gives back naive datetimes. The route compares them with an aware "now".
Before the fix, this raised "TypeError: can't compare offset-naive and
offset-aware datetimes".
"""

import datetime

import pytest

from app.models import Invitation, Library, MediaServer

CODES = ["ACTIVE123", "UNLIMITED789", "EXPIRED999"]


def _server(session, name):
    server = MediaServer(
        name=name, server_type="plex", url="http://plex.local", api_key="key"
    )
    session.add(server)
    session.commit()
    return server


@pytest.fixture
def server(session):
    server = _server(session, "Test Plex Server")
    session.add_all(
        [
            Library(name="Movies", server_id=server.id, external_id="1"),
            Library(name="TV Shows", server_id=server.id, external_id="2"),
        ]
    )
    session.commit()
    return server


@pytest.fixture
def invitations(session, server):
    """Add an active, an unlimited, and an expired invitation on the server."""
    now = datetime.datetime.now(datetime.UTC)
    for code, expires, used, unlimited in [
        ("ACTIVE123", now + datetime.timedelta(days=30), False, False),
        ("UNLIMITED789", None, False, True),
        ("EXPIRED999", now - datetime.timedelta(days=30), True, False),
    ]:
        invitation = Invitation(
            code=code, expires=expires, used=used, unlimited=unlimited
        )
        invitation.servers.append(server)
        invitation.libraries.extend(server.libraries)
        session.add(invitation)
    session.commit()


def _table(client, data=None):
    response = client.post("/invite/table", data=data)
    assert response.status_code == 200
    return response.data.decode("utf-8")


def test_invite_table_with_stored_expiry_dates(admin_client, invitations):
    html = _table(admin_client)

    for code in CODES:
        assert code in html
    # Only the expired invitation gets the "Expired" badge.
    assert html.count("Expired") == 1


def test_invite_table_with_filter_by_server(admin_client, session, server, invitations):
    other = _server(session, "Other Server")
    other_invitation = Invitation(code="OTHERSRV1", used=False, unlimited=False)
    other_invitation.servers.append(other)
    session.add(other_invitation)
    session.commit()

    html = _table(admin_client, {"server": str(server.id)})

    for code in CODES:
        assert code in html
    assert "OTHERSRV1" not in html


def test_invite_table_empty_state(admin_client):
    assert "There are currently no invitations." in _table(admin_client)
