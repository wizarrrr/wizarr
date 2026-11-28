"""Tests for the RomM live-activity mapping and the server version.

The failure behaviour of now_playing() is tested with the other clients in
test_now_playing_errors.py.
"""

import pytest

from app.services.media.romm import RommClient

SAMPLE_ENTRY = {
    "user_id": 7,
    "username": "alice",
    "avatar_path": "users/7/avatar.jpg",
    "rom_id": 42,
    "rom_name": "Super Mario Bros.",
    "rom_cover_path": "roms/nes/super-mario-bros/cover.jpg",
    "screenshot_path": "/api/saves/99/content?timestamp=1",
    "platform_slug": "nes",
    "platform_name": "Nintendo Entertainment System",
    "device_id": "muos-handheld-1",
    "device_type": "muOS",
    "started_at": "2026-09-11T12:00:00+00:00",
}


def _client():
    """Build a RommClient without running __init__ (no DB/network)."""
    client = RommClient.__new__(RommClient)
    client.url = "https://romm.example.com"
    client.server_id = 1
    return client


def test_now_playing_entry_maps_core_fields():
    session = _client()._now_playing_entry(SAMPLE_ENTRY)

    assert session["user_name"] == "alice"
    assert session["media_title"] == "Super Mario Bros."
    assert session["session_id"] == "7:muos-handheld-1:42"
    assert session["user_id"] == 7
    assert session["media_type"] == "game"
    assert session["media_id"] == 42
    assert session["state"] == "playing"
    assert session["client"] == "muOS"
    assert session["device_name"] == ""  # RomM has no separate device name
    assert session["platform"] == "Nintendo Entertainment System"
    # Fields the now-playing card template reads unconditionally
    assert session["progress"] == 0.0
    assert session["transcoding_info"]["is_transcoding"] is False
    assert session["transcoding_info"]["direct_play"] is True


def test_now_playing_entry_metadata():
    session = _client()._now_playing_entry(SAMPLE_ENTRY)

    assert session["metadata"]["romm_platform_slug"] == "nes"
    assert session["metadata"]["romm_device_id"] == "muos-handheld-1"
    assert session["metadata"]["romm_started_at"] == "2026-09-11T12:00:00+00:00"
    assert session["metadata"]["romm_screenshot_path"].startswith("/api/saves/")


def test_session_id_changes_when_the_game_changes():
    """RomM keeps its user_id:device_id key when a player switches games.

    The session id must change with the game. Otherwise Wizarr renames the
    running session to the new game and credits the old play time to it.
    """
    client = _client()
    zelda = {**SAMPLE_ENTRY, "rom_id": 43, "rom_name": "The Legend of Zelda"}

    mario_id = client._now_playing_entry(SAMPLE_ENTRY)["session_id"]
    zelda_id = client._now_playing_entry(zelda)["session_id"]

    assert mario_id != zelda_id


@pytest.mark.parametrize(
    "entry",
    [
        {},
        {"user_id": 7, "rom_id": 42},
        {"device_id": "muos-handheld-1", "rom_id": 42},
        {"user_id": 7, "device_id": "muos-handheld-1"},
        {"user_id": None, "device_id": "muos-handheld-1", "rom_id": 42},
        {"user_id": 7, "device_id": "", "rom_id": 42},
    ],
)
def test_now_playing_entry_rejects_untrackable_entries(entry):
    """Without user_id, device_id and rom_id the session cannot be tracked."""
    with pytest.raises(ValueError, match="no user_id, device_id or rom_id"):
        _client()._now_playing_entry(entry)


def test_cover_url_builds_absolute_url():
    assert _client()._cover_url(SAMPLE_ENTRY) == (
        "https://romm.example.com/assets/romm/resources/"
        "roms/nes/super-mario-bros/cover.jpg"
    )


def test_cover_url_empty_when_no_cover():
    assert _client()._cover_url({"rom_cover_path": ""}) == ""


class _Response:
    """The part of a ``requests`` response that ``_server_version`` reads."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"SYSTEM": {"VERSION": "5.4.1"}}, "5.4.1"),
        ({"SYSTEM": {}}, "Unknown"),
        (["not", "a", "dict"], "Unknown"),
    ],
)
def test_server_version_from_heartbeat(monkeypatch, payload, expected):
    client = _client()
    paths = []

    def fake_get(path):
        paths.append(path)
        return _Response(payload)

    monkeypatch.setattr(client, "get", fake_get)

    assert client._server_version() == expected
    assert paths == ["/api/heartbeat"]


def test_server_version_unknown_on_failure(monkeypatch):
    client = _client()

    def boom(url):
        raise ConnectionError("down")

    monkeypatch.setattr(client, "get", boom)

    assert client._server_version() == "Unknown"
