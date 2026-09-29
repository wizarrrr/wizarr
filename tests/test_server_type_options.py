"""The server-type picker in the create and edit modals comes from the client registry.

Both modals used to hardcode seven <option>s, so Drop and Navidrome could not be
picked when adding a server. Editing an existing Drop or Navidrome server was worse:
no option matched, the browser submitted the first one (Plex), and the connection
check then ran against the wrong server type, so the edit could never be saved.
"""

import re
from unittest.mock import patch

from app.models import AdminAccount, MediaServer
from app.services.media.client_base import CLIENTS
from app.services.media.service import server_type_choices


def _login(client, session):
    admin = AdminAccount(username="testadmin")
    admin.set_password("TestPass123")
    session.add(admin)
    session.commit()
    resp = client.post(
        "/login", data={"username": "testadmin", "password": "TestPass123"}
    )
    assert resp.status_code in {200, 302, 303}


def _server(session, server_type):
    server = MediaServer(
        name=f"My {server_type}",
        server_type=server_type,
        url=f"http://{server_type}.local",
        api_key="token",
    )
    session.add(server)
    session.commit()
    return server


def _options(html):
    return re.findall(r'<option value="([^"]+)"', html)


def _selected(html):
    match = re.search(r'<option value="([^"]+)"\s+selected', html)
    return match.group(1) if match else None


def test_choices_cover_every_registered_client(app):
    with app.app_context():
        values = [value for value, _ in server_type_choices()]

    assert set(values) == set(CLIENTS)
    assert "drop" in values
    assert "navidrome" in values
    # the long-standing order is kept for the types that were already listed
    assert values[:3] == ["plex", "jellyfin", "emby"]


def test_labels_match_the_previous_hardcoded_ones(app):
    with app.app_context():
        labels = dict(server_type_choices())

    assert labels["plex"] == "Plex"
    assert labels["audiobookshelf"] == "Audiobookshelf"
    assert labels["navidrome"] == "Navidrome"


def test_an_unregistered_current_type_is_kept(app):
    """A server whose client is missing must not be re-typed on save."""
    with app.app_context():
        choices = server_type_choices("mystery")

    assert choices[0] == ("mystery", "Mystery")


def test_create_modal_offers_every_registered_type(client, session):
    _login(client, session)
    html = client.get("/settings/servers/create").get_data(as_text=True)

    assert set(_options(html)) >= set(CLIENTS)


def test_edit_modal_preselects_navidrome(client, session):
    _login(client, session)
    server = _server(session, "navidrome")

    html = client.get(f"/settings/servers/{server.id}/edit").get_data(as_text=True)

    assert _selected(html) == "navidrome"


def test_editing_a_navidrome_server_keeps_its_type(client, session):
    """Round-trip the form exactly as the browser would submit it."""
    _login(client, session)
    server = _server(session, "navidrome")

    html = client.get(f"/settings/servers/{server.id}/edit").get_data(as_text=True)
    submitted_type = _selected(html)
    assert submitted_type is not None, "no option selected: browser would send Plex"

    with patch(
        "app.blueprints.media_servers.routes.check_navidrome",
        return_value=(True, ""),
    ) as check:
        resp = client.post(
            f"/settings/servers/{server.id}/edit",
            data={
                "server_name": "Renamed",
                "server_type": submitted_type,
                "server_url": "http://navidrome.local:4533",
                "api_key": "token",
            },
        )

    assert resp.status_code in {302, 303}
    check.assert_called_once()
    session.refresh(server)
    assert server.server_type == "navidrome"
    assert server.name == "Renamed"
    assert server.url == "http://navidrome.local:4533"
