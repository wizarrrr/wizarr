"""Regression tests for Navidrome Subsonic authentication."""

from __future__ import annotations

import hashlib
from unittest.mock import Mock, patch

from app.extensions import db
from app.models import MediaServer
from app.services.media.navidrome import NavidromeClient
from app.services.servers import check_navidrome


def test_navidrome_client_uses_configured_admin_username_and_subsonic_hash():
    client = object.__new__(NavidromeClient)
    client.token = "correct horse battery staple"
    client.username = "music-admin"

    with patch(
        "app.services.media.navidrome.random.choices", return_value=list("a1B2c3")
    ):
        params = client._generate_auth_params()

    assert params["u"] == "music-admin"
    assert params["s"] == "a1B2c3"
    assert params["t"] == hashlib.md5(  # noqa: S324
        b"correct horse battery staplea1B2c3"
    ).hexdigest()


def test_navidrome_connection_check_uses_configured_username_and_md5():
    response = Mock()
    response.status_code = 200
    response.url = "https://music.example/rest/ping"
    response.json.return_value = {"subsonic-response": {"status": "ok"}}

    with (
        patch("app.services.servers.random.choices", return_value=list("a1B2c3")),
        patch("app.services.servers.requests.get", return_value=response) as get,
    ):
        ok, message = check_navidrome(
            "https://music.example/",
            "correct horse battery staple",
            username="music-admin",
        )

    assert ok is True
    assert message == ""
    params = get.call_args.kwargs["params"]
    assert params["u"] == "music-admin"
    assert params["s"] == "a1B2c3"
    assert params["t"] == hashlib.md5(
        b"correct horse battery staplea1B2c3"
    ).hexdigest()
    assert get.call_args.args[0] == "https://music.example/rest/ping"


def test_navidrome_connection_check_defaults_legacy_username_to_admin():
    response = Mock()
    response.status_code = 200
    response.url = "https://music.example/rest/ping"
    response.json.return_value = {"subsonic-response": {"status": "ok"}}

    with (
        patch("app.services.servers.random.choices", return_value=list("a1B2c3")),
        patch("app.services.servers.requests.get", return_value=response) as get,
    ):
        ok, _ = check_navidrome("https://music.example", "password")

    assert ok is True
    assert get.call_args.kwargs["params"]["u"] == "admin"


def test_navidrome_client_reads_username_from_saved_server(app):
    with app.app_context():
        server = MediaServer(
            name="Test Music",
            server_type="navidrome",
            url="https://music.example",
            api_key="password",
            server_username="music-admin",
        )
        db.session.add(server)
        db.session.flush()

        client = NavidromeClient(media_server=server)

        assert client.username == "music-admin"
        db.session.rollback()


def test_navidrome_client_defaults_legacy_server_rows_to_admin(app):
    with app.app_context():
        server = MediaServer(
            name="Legacy Music",
            server_type="navidrome",
            url="https://music.example",
            api_key="password",
            server_username=None,
        )
        db.session.add(server)
        db.session.flush()

        client = NavidromeClient(media_server=server)

        assert client.username == "admin"
        db.session.rollback()
