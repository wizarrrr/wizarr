from app.services.media.auth_headers import media_browser_auth_headers
from app.services.media.jellyfin import JellyfinClient
from app.services.servers import check_jellyfin_or_emby_internal


class _Response:
    status_code = 200
    url = "http://jellyfin.local/Users"


def test_media_browser_auth_headers_include_modern_and_legacy_tokens():
    headers = media_browser_auth_headers("test-token")

    assert headers["Accept"] == "application/json"
    assert headers["Authorization"] == 'MediaBrowser Token="test-token"'
    assert headers["X-Emby-Token"] == "test-token"


def test_jellyfin_client_uses_modern_media_browser_auth_header():
    client = object.__new__(JellyfinClient)
    client.token = "test-token"

    headers = client._headers()

    assert headers["Authorization"] == 'MediaBrowser Token="test-token"'
    assert headers["X-Emby-Token"] == "test-token"


def test_jellyfin_health_check_uses_modern_media_browser_auth_header(monkeypatch):
    captured = {}

    def fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("app.services.servers.requests.get", fake_get)

    assert check_jellyfin_or_emby_internal("http://jellyfin.local", "test-token") == (
        True,
        "",
    )
    assert captured["url"] == "http://jellyfin.local/Users"
    assert captured["headers"]["Authorization"] == 'MediaBrowser Token="test-token"'
    assert captured["headers"]["X-Emby-Token"] == "test-token"
    assert captured["timeout"] == 10
