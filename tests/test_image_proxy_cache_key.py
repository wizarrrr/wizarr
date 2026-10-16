"""The image proxy cache survives the hourly token change, and posters are small.

The server-side image cache was keyed on the token. A token contains an hourly
bucket, so the cache went cold every hour. It is now keyed on the server and
the normalized upstream URL. A valid token is still needed for each request.
"""

from typing import ClassVar
from urllib.parse import unquote_plus

import pytest

import app.services.image_proxy as image_proxy_module
from app.services.image_proxy import ImageProxyService
from app.services.media.emby import EmbyClient
from app.services.media.jellyfin import (
    NOW_PLAYING_BACKDROP_PARAMS,
    NOW_PLAYING_POSTER_PARAMS,
    POSTER_IMAGE_PARAMS,
    JellyfinClient,
)

pytestmark = pytest.mark.usefixtures("clear_media_caches")

UPSTREAM = "http://cdn.example.com/poster.jpg?b=2&a=1"


class _Clock:
    def __init__(self, current: float):
        self.current = current

    def time(self) -> float:
        return self.current


class _FakeResponse:
    status_code = 200
    headers: ClassVar = {"Content-Type": "image/jpeg"}
    content = b"\xff\xd8\xff-poster"

    def raise_for_status(self):
        return None

    def iter_content(self, _chunk_size):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def upstream(monkeypatch):
    calls = []

    class _Session:
        def get(self, url, **_kwargs):
            calls.append(url)
            return _FakeResponse()

    monkeypatch.setattr(
        ImageProxyService,
        "get_session",
        classmethod(lambda cls, url, server_id: _Session()),
    )
    return calls


def test_cache_key_is_the_upstream_image_not_the_token():
    key = ImageProxyService.image_cache_key(None, UPSTREAM)

    assert key == ImageProxyService.image_cache_key(
        None, "HTTP://CDN.example.COM/poster.jpg?a=1&b=2#frag"
    )
    assert key != ImageProxyService.image_cache_key(7, UPSTREAM)
    assert key != ImageProxyService.image_cache_key(
        None, "http://cdn.example.com/other.jpg?a=1&b=2"
    )


def test_cache_hit_survives_the_hourly_token_change(app, client, monkeypatch, upstream):
    boundary = 1_800_000_000.0  # exact hourly bucket boundary
    clock = _Clock(boundary - 10)
    monkeypatch.setattr(image_proxy_module, "time", clock)

    with app.app_context():
        first_token = ImageProxyService.generate_token(UPSTREAM)
    assert client.get(f"/image-proxy?token={first_token}").status_code == 200

    # Twenty seconds later the bucket changed, so the page gets a new token
    # for the same image.
    clock.current = boundary + 10
    with app.app_context():
        second_token = ImageProxyService.generate_token(UPSTREAM)
    assert second_token != first_token

    response = client.get(f"/image-proxy?token={second_token}")

    assert response.status_code == 200
    assert response.data == _FakeResponse.content
    assert len(upstream) == 1  # served from the cache


def test_cached_image_still_needs_a_valid_token(client, upstream):
    ImageProxyService.cache_image(
        ImageProxyService.image_cache_key(None, UPSTREAM), b"cached", "image/jpeg"
    )

    assert client.get("/image-proxy?token=not-a-valid-token").status_code == 403
    assert upstream == []


def test_proxied_images_are_cached_by_the_browser_for_a_day(app, client, upstream):
    with app.app_context():
        token = ImageProxyService.generate_token(UPSTREAM)

    response = client.get(f"/image-proxy?token={token}")

    assert response.headers["Cache-Control"] == "public, max-age=86400"


# ─── Resized posters ────────────────────────────────────────────────────────


def _decode_url(proxy_url: str, app) -> str:
    token = unquote_plus(proxy_url.split("token=", 1)[1])
    with app.app_context():
        return ImageProxyService.validate_token(token)["url"]


class _Items:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


@pytest.mark.parametrize("cls", [JellyfinClient, EmbyClient])
def test_join_page_posters_are_resized(app, cls):
    client = cls.__new__(cls)
    client.url = "http://media.local"
    client.token = "admin-key"
    client.server_id = None
    client.get = lambda *_a, **_kw: _Items({"Items": [{"Id": "m1"}]})

    with app.app_context():
        (poster,) = client.get_movie_posters(limit=1)

    upstream_url = _decode_url(poster, app)
    assert upstream_url.startswith("http://media.local/Items/m1/Images/Primary?")
    assert POSTER_IMAGE_PARAMS in upstream_url
    assert "maxWidth=240" in POSTER_IMAGE_PARAMS


def test_now_playing_artwork_is_resized():
    client = JellyfinClient.__new__(JellyfinClient)
    client.url = "http://media.local"
    client.token = "admin-key"

    urls = client._get_artwork_urls("item-1", "movie")

    assert urls["artwork_url"] == (
        "http://media.local/Items/item-1/Images/Primary"
        f"?{NOW_PLAYING_POSTER_PARAMS}&api_key=admin-key"
    )
    # The backdrop is shown blurred, so it is smaller.
    assert urls["thumbnail_url"] == (
        "http://media.local/Items/item-1/Images/Backdrop"
        f"?{NOW_PLAYING_BACKDROP_PARAMS}&api_key=admin-key"
    )
