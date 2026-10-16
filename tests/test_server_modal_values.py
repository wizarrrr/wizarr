"""A server modal keeps the typed values after a failed connection test (#727).

No test uses the network: the connection check always fails.
"""

import base64
import re

import pytest

from app.extensions import db
from app.models import MediaServer


@pytest.fixture(autouse=True)
def _failing_connection(monkeypatch):
    monkeypatch.setattr(
        "app.blueprints.media_servers.routes.check_server_connection",
        lambda *_args: (False, "Connection refused"),
    )


def _selected(html: str, server_type: str) -> bool:
    return re.search(rf'<option value="{server_type}"\s+selected>', html) is not None


def _checked(html: str, name: str) -> bool:
    pattern = rf'name="{name}"\s+type="checkbox"\s+value="true"\s+checked'
    return re.search(pattern, html) is not None


def test_create_modal_keeps_typed_values(admin_client):
    response = admin_client.post(
        "/settings/servers/create",
        data={
            "server_name": "My Jellyfin",
            "server_type": "jellyfin",
            "server_url": "http://jf.local:8096",
            "external_url": "https://jf.example.com",
            "api_key": "typed-key",
            "allow_downloads": "true",
        },
        headers={"HX-Request": "true"},
    )

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.headers["HX-Retarget"] == "#create-server-modal"
    assert "Connection refused" in html
    assert 'value="My Jellyfin"' in html
    assert _selected(html, "jellyfin")
    assert not _selected(html, "plex")
    assert 'value="http://jf.local:8096"' in html
    assert 'value="https://jf.example.com"' in html
    assert 'value="typed-key"' in html
    assert _checked(html, "allow_downloads")
    assert not _checked(html, "allow_live_tv")
    assert MediaServer.query.count() == 0


def test_create_modal_does_not_echo_the_password(admin_client):
    response = admin_client.post(
        "/settings/servers/create",
        data={
            "server_name": "My RomM",
            "server_type": "romm",
            "server_url": "http://romm.local",
            "server_username": "romm-admin",
            "server_password": "s3cret-pass",
        },
        headers={"HX-Request": "true"},
    )

    html = response.get_data(as_text=True)
    credentials = base64.b64encode(b"romm-admin:s3cret-pass").decode()
    assert _selected(html, "romm")
    assert 'value="romm-admin"' in html
    assert "s3cret-pass" not in html
    assert credentials not in html


def test_edit_modal_keeps_typed_values(admin_client, session):
    server = MediaServer(
        name="Old Name",
        server_type="jellyfin",
        url="http://old.local",
        api_key="old-key",
        allow_downloads=True,
        verified=True,
    )
    session.add(server)
    session.commit()

    opened = admin_client.get(f"/settings/servers/{server.id}/edit")
    assert 'value="Old Name"' in opened.get_data(as_text=True)

    response = admin_client.post(
        f"/settings/servers/{server.id}/edit",
        data={
            "server_name": "New Name",
            "server_type": "emby",
            "server_url": "http://new.local",
            "external_url": "",
            "api_key": "new-key",
        },
        headers={"HX-Request": "true"},
    )

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Connection refused" in html
    assert 'value="New Name"' in html
    assert 'value="Old Name"' not in html
    assert _selected(html, "emby")
    assert not _selected(html, "jellyfin")
    assert 'value="http://new.local"' in html
    assert 'value="new-key"' in html
    assert not _checked(html, "allow_downloads")
    db.session.expire_all()
    unchanged = db.session.get(MediaServer, server.id)
    assert unchanged is not None
    assert unchanged.name == "Old Name"
