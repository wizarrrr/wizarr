"""Regression tests for wizarrrr/wizarr#1343.

The Overseerr/Jellyseerr (Info Only) connection type rendered the required
``name`` and ``media_server_id`` fields as ``disabled``. Disabled inputs are not
submitted by browsers, so ``ConnectionForm`` never validated and the connection
could not be created through the UI.
"""

import re

import pytest

from app.extensions import db
from app.models import AdminAccount, Connection, MediaServer


@pytest.fixture
def admin_client(client, app):
    """A test client logged in as an admin account."""
    with app.app_context():
        if AdminAccount.query.filter_by(username="conn-admin").first() is None:
            acc = AdminAccount(username="conn-admin")
            acc.set_password("Password1")
            db.session.add(acc)
            db.session.commit()
    resp = client.post(
        "/login", data={"username": "conn-admin", "password": "Password1"}
    )
    assert resp.status_code in {302, 303}
    return client


@pytest.fixture
def media_server(app):
    with app.app_context():
        server = MediaServer(
            name="Jellyfin",
            server_type="jellyfin",
            url="http://jellyfin:8096",
            api_key="test-key",
        )
        db.session.add(server)
        db.session.commit()
        return server.id


def _field_tag(html: str, tag: str, name: str) -> str:
    match = re.search(rf"<{tag}\b[^>]*\bname=\"{name}\"[^>]*>", html)
    assert match is not None, f"<{tag} name={name!r}> not rendered"
    return match.group(0)


@pytest.mark.parametrize("htmx", [False, True], ids=["page", "modal"])
def test_overseerr_form_required_fields_are_not_disabled(
    admin_client, media_server, htmx
):
    """Both connection form templates must keep name/media_server_id submittable."""
    headers = {"HX-Request": "true"} if htmx else {}
    resp = admin_client.get(
        "/settings/connections/create?connection_type=overseerr", headers=headers
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "disabled" not in _field_tag(html, "input", "name")
    assert "disabled" not in _field_tag(html, "select", "media_server_id")


def test_create_overseerr_connection_persists(admin_client, media_server, app):
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
    assert resp.status_code in {200, 302, 303}

    with app.app_context():
        conn = Connection.query.filter_by(name="Jellyseerr").first()
        assert conn is not None
        assert conn.connection_type == "overseerr"
        assert conn.media_server_id == media_server
        assert conn.url == "https://jellyseerr.example.com"
