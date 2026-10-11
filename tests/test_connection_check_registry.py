"""Connection checks are owned by each media client and dispatched by the registry.

The create/edit server routes, and the legacy settings route, each carried an
if/elif chain over server types that fell through to ``check_jellyfin``. A type
missing from a chain, including any new client, was silently checked as if it
were Jellyfin and refused with a misleading error. The chains now defer to
``MediaClient.check_connection`` via ``check_server_connection``.
"""

import base64
from unittest.mock import patch

import pytest

from app.blueprints.settings.routes import _check_server_connection
from app.models import AdminAccount
from app.services.media.client_base import CLIENTS, MediaClient
from app.services.media.service import check_server_connection

EXPECTED = {
    "plex": "check_plex",
    "jellyfin": "check_jellyfin",
    "emby": "check_emby",
    "audiobookshelf": "check_audiobookshelf",
    "romm": "check_romm",
    "komga": "check_komga",
    "kavita": "check_kavita",
    "navidrome": "check_navidrome",
    "drop": "check_drop",
}


def _login(client, session):
    admin = AdminAccount(username="testadmin")
    admin.set_password("TestPass123")
    session.add(admin)
    session.commit()
    client.post("/login", data={"username": "testadmin", "password": "TestPass123"})


def test_every_built_in_client_has_its_own_check():
    assert set(EXPECTED) <= set(CLIENTS)
    base = MediaClient.check_connection.__func__
    for name in EXPECTED:
        assert CLIENTS[name].check_connection.__func__ is not base, name


@pytest.mark.parametrize(("server_type", "fn"), sorted(EXPECTED.items()))
def test_each_type_runs_its_own_check(server_type, fn):
    with patch(f"app.services.servers.{fn}", return_value=(True, "ok")) as check:
        result = check_server_connection(server_type, "http://srv.local", "tok")

    assert result == (True, "ok")
    check.assert_called_once_with("http://srv.local", "tok")


def test_emby_does_not_inherit_the_jellyfin_check():
    """EmbyClient subclasses JellyfinClient, so it must override explicitly."""
    with (
        patch("app.services.servers.check_emby", return_value=(True, "")) as emby,
        patch("app.services.servers.check_jellyfin", return_value=(True, "")) as jf,
    ):
        check_server_connection("emby", "http://emby.local", "tok")

    emby.assert_called_once()
    jf.assert_not_called()


def test_unknown_type_is_refused_by_name_not_checked_as_jellyfin():
    with patch("app.services.servers.check_jellyfin") as jf:
        ok, message = check_server_connection("mystery", "http://x.local", "tok")

    assert ok is False
    assert "mystery" in message
    jf.assert_not_called()


def test_base_default_refuses():
    class Unchecked(MediaClient):
        pass

    ok, message = Unchecked.check_connection("http://x.local", "tok")
    assert ok is False
    assert "No connection check" in message


def test_create_route_refuses_an_unknown_type(client, session):
    _login(client, session)
    with patch("app.services.servers.check_jellyfin") as jf:
        resp = client.post(
            "/settings/servers/create",
            data={
                "server_name": "X",
                "server_type": "mystery",
                "server_url": "http://x.local",
                "api_key": "tok",
            },
        )

    assert "mystery" in resp.get_data(as_text=True)
    jf.assert_not_called()


def test_create_route_still_derives_the_romm_token(client, session):
    _login(client, session)
    with patch("app.services.servers.check_romm", return_value=(False, "no")) as romm:
        client.post(
            "/settings/servers/create",
            data={
                "server_name": "R",
                "server_type": "romm",
                "server_url": "http://romm.local",
                "server_username": "u",
                "server_password": "p",
            },
        )

    romm.assert_called_once_with("http://romm.local", base64.b64encode(b"u:p").decode())


def test_settings_check_still_derives_the_romm_token():
    with patch("app.services.servers.check_romm", return_value=(True, "")) as romm:
        _check_server_connection(
            {
                "server_type": "romm",
                "server_url": "http://romm.local",
                "server_username": "u",
                "server_password": "p",
            }
        )

    romm.assert_called_once_with("http://romm.local", base64.b64encode(b"u:p").decode())


def test_settings_check_refuses_an_unknown_type():
    with patch("app.services.servers.check_jellyfin") as jf:
        ok, message = _check_server_connection(
            {"server_type": "mystery", "server_url": "http://x.local", "api_key": "t"}
        )

    assert ok is False
    assert "mystery" in message
    jf.assert_not_called()
