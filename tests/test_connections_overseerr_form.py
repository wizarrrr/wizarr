"""Regression tests for wizarrrr/wizarr#1343.

The Overseerr/Jellyseerr (Info Only) connection type rendered the required
``name`` and ``media_server_id`` fields as ``disabled``. Disabled inputs are not
submitted by browsers, so ``ConnectionForm`` never validated and the connection
could not be created through the UI.
"""

import re

import pytest

from app.models import Connection, MediaServer


@pytest.fixture
def media_server(session):
    server = MediaServer(
        name="Jellyfin",
        server_type="jellyfin",
        url="http://jellyfin:8096",
        api_key="test-key",
    )
    session.add(server)
    session.commit()
    yield server.id
    # The conftest cleanup does not delete connections.
    session.rollback()
    session.query(Connection).delete()
    session.commit()


def _field_tag(html: str, tag: str, name: str) -> str:
    match = re.search(rf"<{tag}\b[^>]*\bname=\"{name}\"[^>]*>", html)
    assert match is not None, f"<{tag} name={name!r}> not rendered"
    return match.group(0)


@pytest.mark.parametrize("htmx", [False, True], ids=["page", "modal"])
def test_overseerr_form_renders_for_seerr(admin_client, media_server, htmx):
    """Both connection form templates must render a usable Seerr form."""
    headers = {"HX-Request": "true"} if htmx else {}
    resp = admin_client.get(
        "/settings/connections/create?connection_type=overseerr", headers=headers
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # #1343: the browser must submit the required fields.
    assert "disabled" not in _field_tag(html, "input", "name")
    assert "disabled" not in _field_tag(html, "select", "media_server_id")

    # #1419: the label names Seerr, but the stored value stays "overseerr" so
    # that existing connections keep their type.
    option = re.search(
        r"<option\b[^>]*\bvalue=\"overseerr\"[^>]*>([^<]*)</option>", html
    )
    assert option is not None
    assert option.group(1).strip() == "Seerr (Overseerr/Jellyseerr)"
    assert "Seerr Information" in html


def test_create_overseerr_connection_persists(admin_client, session, media_server):
    """Submitting the info-only form with its required fields creates the row."""
    resp = admin_client.post(
        "/settings/connections/create",
        data={
            "connection_type": "overseerr",
            "name": "Jellyseerr",
            "media_server_id": str(media_server),
            "url": "https://jellyseerr.example.com",
            "api_key": "",
        },
    )
    assert resp.status_code == 302

    conn = Connection.query.filter_by(name="Jellyseerr").one()
    assert conn.connection_type == "overseerr"
    assert conn.media_server_id == media_server
    assert conn.url == "https://jellyseerr.example.com"
