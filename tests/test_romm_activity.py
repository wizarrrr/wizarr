"""Tests for RomM live-activity mapping (now_playing)."""

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


def test_activity_to_session_maps_core_fields():
    client = _client()
    session = client._activity_to_session(SAMPLE_ENTRY)

    assert session["user_name"] == "alice"
    assert session["media_title"] == "Super Mario Bros."
    assert session["session_id"] == "7:muos-handheld-1"
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


def test_activity_to_session_metadata():
    client = _client()
    session = client._activity_to_session(SAMPLE_ENTRY)

    assert session["metadata"]["romm_platform_slug"] == "nes"
    assert session["metadata"]["romm_device_id"] == "muos-handheld-1"
    assert session["metadata"]["romm_started_at"] == "2026-09-11T12:00:00+00:00"
    assert session["metadata"]["romm_screenshot_path"].startswith("/api/saves/")


@pytest.mark.parametrize(
    "entry",
    [
        {},
        {"user_id": 7},
        {"device_id": "muos-handheld-1"},
        {"user_id": None, "device_id": "muos-handheld-1"},
        {"user_id": 7, "device_id": ""},
    ],
)
def test_activity_to_session_rejects_untrackable_entries(entry):
    """user_id:device_id keys the session; without both it is untrackable."""
    client = _client()
    with pytest.raises(ValueError, match="missing user_id/device_id"):
        client._activity_to_session(entry)


def test_now_playing_skips_untrackable_entries(monkeypatch):
    client = _client()

    class FakeResponse:
        def json(self):
            return [SAMPLE_ENTRY, {"username": "ghost"}]

    monkeypatch.setattr(client, "get", lambda url: FakeResponse())

    sessions = client.now_playing()

    assert [s["session_id"] for s in sessions] == ["7:muos-handheld-1"]


def test_now_playing_fetches_once_within_cache_ttl(monkeypatch):
    """A dashboard render touching now_playing() twice hits /api/activity once."""
    client = _client()
    calls = []

    class FakeResponse:
        def json(self):
            return [SAMPLE_ENTRY]

    def fake_get(url):
        calls.append(url)
        return FakeResponse()

    monkeypatch.setattr(client, "get", fake_get)

    first = client.now_playing()
    second = client.now_playing()

    assert first == second
    assert len(calls) == 1

    # Expired cache fetches again
    client._now_playing_cache = (
        client._now_playing_cache[0] - RommClient._NOW_PLAYING_CACHE_TTL - 1,
        first,
    )
    client.now_playing()
    assert len(calls) == 2


def test_cover_url_builds_absolute_url():
    client = _client()
    client.url = "https://romm.example.com"

    result = client._cover_url(SAMPLE_ENTRY)

    assert result == (
        "https://romm.example.com/assets/romm/resources/"
        "roms/nes/super-mario-bros/cover.jpg"
    )


def test_cover_url_empty_when_no_cover():
    client = _client()
    client.url = "https://romm.example.com"
    assert client._cover_url({"rom_cover_path": ""}) == ""


def test_server_version_from_heartbeat(monkeypatch):
    client = _client()

    class FakeResponse:
        def json(self):
            return {"SYSTEM": {"VERSION": "4.3.2"}}

    monkeypatch.setattr(client, "get", lambda url: FakeResponse())
    assert client._server_version() == "4.3.2"


def test_server_version_unknown_on_failure(monkeypatch):
    client = _client()

    def boom(url):
        raise ConnectionError("down")

    monkeypatch.setattr(client, "get", boom)
    assert client._server_version() == "Unknown"
