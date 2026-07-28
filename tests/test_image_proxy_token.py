"""Confidentiality and integrity tests for image-proxy tokens.

Proxy tokens are embedded in pages served to invited users (the
``recently_added_media`` wizard widget, among others), so they must never
disclose the media server's admin credentials or the internal upstream URL.
"""

import base64
import json
from typing import ClassVar
from urllib.parse import unquote_plus

import pytest
from requests.structures import CaseInsensitiveDict

import app.services.image_proxy as image_proxy_module
from app.services.image_proxy import ImageProxyService
from app.services.media.emby import EmbyClient
from app.services.media.jellyfin import JellyfinClient

PLEX_TOKEN = "sUpErSeCrEtAdM1nT0k3n"  # test fixture, not a real credential
POSTER_URL = (
    "http://plex.internal:32400/library/metadata/12345/thumb/1700000000"
    f"?X-Plex-Token={PLEX_TOKEN}"
)
POSTER_URL_CLEAN = "http://plex.internal:32400/library/metadata/12345/thumb/1700000000"


def _decode(token: str) -> bytes:
    """Base64url-decode a token the way an attacker with the HTML would."""
    padding = (4 - len(token) % 4) % 4
    return base64.urlsafe_b64decode(token + ("=" * padding))


class _FrozenTime:
    def __init__(self, current: float):
        self.current = current

    def time(self) -> float:
        return self.current


@pytest.fixture(autouse=True)
def _clear_caches():
    """validate_token() short-circuits on the token cache, so isolate every test."""
    ImageProxyService._token_cache.clear()
    ImageProxyService._image_cache.clear()
    ImageProxyService._total_image_bytes = 0
    ImageProxyService._cipher_key_cache.clear()
    ImageProxyService._server_url_cache.clear()
    ImageProxyService._server_header_cache.clear()
    yield
    ImageProxyService._token_cache.clear()
    ImageProxyService._image_cache.clear()
    ImageProxyService._total_image_bytes = 0
    ImageProxyService._cipher_key_cache.clear()
    ImageProxyService._server_url_cache.clear()
    ImageProxyService._server_header_cache.clear()


# ─── Confidentiality ────────────────────────────────────────────────────────


def test_token_does_not_disclose_admin_token(app):
    """The whole point: nothing recoverable from the token the browser receives."""
    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=1)

    assert PLEX_TOKEN not in token

    raw = _decode(token)
    assert PLEX_TOKEN.encode() not in raw
    assert b"X-Plex-Token" not in raw
    assert b"plex.internal" not in raw
    assert b"library/metadata" not in raw


@pytest.mark.parametrize(
    "param",
    [
        "X-Plex-Token",
        "x-plex-token",
        "X-Emby-Token",
        "X-MediaBrowser-Token",
        "X-API-Key",
        "api_key",
        "apikey",
        "token",
    ],
)
def test_known_credential_params_are_stripped(app, session, param):
    from app.models import MediaServer

    server = MediaServer(
        name="Media",
        server_type="jellyfin",
        url="http://media.internal:8096",
        api_key="SECRETVALUE",
    )
    session.add(server)
    session.commit()

    url = f"http://media.internal:8096/Items/1/Images/Primary?{param}=SECRETVALUE&maxWidth=300"

    with app.app_context():
        token = ImageProxyService.generate_token(url, server_id=server.id)
        ImageProxyService._token_cache.clear()
        mapping = ImageProxyService.validate_token(token)

    assert mapping is not None
    assert "SECRETVALUE" not in mapping["url"]
    # Non-credential parameters must survive or artwork requests break
    assert "maxWidth=300" in mapping["url"]


def test_userinfo_credentials_are_stripped(app, session):
    from app.models import MediaServer

    server = MediaServer(
        name="Plex",
        server_type="plex",
        url="http://admin:hunter2@plex.internal:32400",
        api_key="key",
    )
    session.add(server)
    session.commit()

    with app.app_context():
        token = ImageProxyService.generate_token(
            "http://admin:hunter2@plex.internal:32400/thumb.jpg",
            server_id=server.id,
        )
        ImageProxyService._token_cache.clear()
        mapping = ImageProxyService.validate_token(token)

    assert mapping is not None
    assert mapping["url"] == "http://plex.internal:32400/thumb.jpg"


def test_url_kept_without_server_id_but_still_opaque(app):
    """Legacy installs have no MediaServer row, so the URL is the only auth path.

    It must still be unreadable by the client.
    """
    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=None)
        ImageProxyService._token_cache.clear()
        mapping = ImageProxyService.validate_token(token)

    assert mapping is not None
    assert mapping["url"] == POSTER_URL
    assert PLEX_TOKEN.encode() not in _decode(token)


# ─── Integrity ──────────────────────────────────────────────────────────────


def test_round_trip(app, session):
    from app.models import MediaServer

    server = MediaServer(
        name="Plex",
        server_type="plex",
        url="http://plex.internal:32400",
        api_key=PLEX_TOKEN,
    )
    session.add(server)
    session.commit()

    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=server.id)
        ImageProxyService._token_cache.clear()
        mapping = ImageProxyService.validate_token(token)

    assert mapping == {"url": POSTER_URL_CLEAN, "server_id": server.id}


def test_tampered_token_rejected(app):
    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=1)
        ImageProxyService._token_cache.clear()

        idx = len(token) // 2
        replacement = "A" if token[idx] != "A" else "B"
        tampered = token[:idx] + replacement + token[idx + 1 :]

        assert ImageProxyService.validate_token(tampered) is None


def test_hand_crafted_payload_rejected(app):
    """An attacker cannot mint a token for an arbitrary URL (SSRF)."""
    payload = json.dumps(
        {
            "url": "http://169.254.169.254/latest/meta-data/",
            "server_id": None,
            "bucket": 0,
        }
    )
    forged = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    with app.app_context():
        assert ImageProxyService.validate_token(forged) is None


def test_token_from_a_different_secret_rejected(app):
    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=1)

    ImageProxyService._token_cache.clear()
    ImageProxyService._cipher_key_cache.clear()

    original = app.config["SECRET_KEY"]
    app.config["SECRET_KEY"] = "a-completely-different-secret"
    try:
        with app.app_context():
            assert ImageProxyService.validate_token(token) is None
    finally:
        app.config["SECRET_KEY"] = original


def test_token_cache_does_not_bypass_secret_rotation(app):
    """A cached mapping belongs to the key that authenticated its token."""
    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=1)

    original = app.config["SECRET_KEY"]
    app.config["SECRET_KEY"] = "a-completely-different-secret"
    try:
        with app.app_context():
            assert ImageProxyService.validate_token(token) is None
    finally:
        app.config["SECRET_KEY"] = original


@pytest.mark.parametrize("token", ["", "not-a-token", "a.b", "AAAA"])
def test_malformed_tokens_rejected(app, token):
    with app.app_context():
        assert ImageProxyService.validate_token(token) is None


# ─── Caching behaviour ──────────────────────────────────────────────────────


def test_token_is_stable_for_the_same_url(app):
    """Deterministic tokens keep the token/image caches effective across workers."""
    with app.app_context():
        first = ImageProxyService.generate_token(POSTER_URL, server_id=1)
        ImageProxyService._token_cache.clear()
        second = ImageProxyService.generate_token(POSTER_URL, server_id=1)

    assert first == second


def test_expired_token_rejected(app, monkeypatch):
    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=1)

    ImageProxyService._token_cache.clear()

    real_time = image_proxy_module.time.time
    skew = ImageProxyService.TOKEN_EXPIRY + ImageProxyService.TOKEN_BUCKET_SECONDS

    class _LaterTime:
        @staticmethod
        def time():
            return real_time() + skew

    monkeypatch.setattr(image_proxy_module, "time", _LaterTime)

    with app.app_context():
        assert ImageProxyService.validate_token(token) is None


def test_cache_does_not_extend_token_lifetime(app, monkeypatch):
    """Re-validating a token near expiry must not extend it via the token cache.

    The cache-hit path used to trust its own insertion time, so a token
    re-validated (and re-cached) just before expiry stayed servable for another
    full TOKEN_EXPIRY. Expiry is now judged from the token's bucket instead.
    """
    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=1)
    ImageProxyService._token_cache.clear()

    real_time = image_proxy_module.time.time

    def _shifted(offset):
        return _FrozenTime(real_time() + offset)

    # Validate just inside the window: still valid, and repopulates the cache.
    near_expiry = (
        ImageProxyService.TOKEN_EXPIRY - ImageProxyService.TOKEN_BUCKET_SECONDS
    )
    monkeypatch.setattr(image_proxy_module, "time", _shifted(near_expiry))
    with app.app_context():
        assert ImageProxyService.validate_token(token) is not None
    assert token in ImageProxyService._token_cache  # cache was repopulated

    # Past the real expiry: the cached entry must not keep serving the token,
    # even though it was inserted only a few hours earlier.
    past_expiry = (
        ImageProxyService.TOKEN_EXPIRY + 5 * ImageProxyService.TOKEN_BUCKET_SECONDS
    )
    monkeypatch.setattr(image_proxy_module, "time", _shifted(past_expiry))
    with app.app_context():
        assert ImageProxyService.validate_token(token) is None


def test_cached_image_does_not_outlive_token_bucket(app, client, monkeypatch):
    """An image-cache hit must still reject its expired access token."""
    start = 1_800_000_000.0  # Exact hourly bucket boundary
    clock = _FrozenTime(start)
    monkeypatch.setattr(image_proxy_module, "time", clock)

    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=None)

    clock.current = start + ImageProxyService.TOKEN_EXPIRY - 60
    ImageProxyService.cache_image(token, b"cached-image", "image/jpeg")

    # The image itself is fresh, but its token is just over 24 hours old.
    clock.current = start + ImageProxyService.TOKEN_EXPIRY + 1
    response = client.get(f"/image-proxy?token={token}")

    assert response.status_code == 403


def test_cached_image_fails_closed_without_secret(app, client):
    """An image-cache hit cannot bypass SECRET_KEY validation."""
    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=None)
    ImageProxyService.cache_image(token, b"cached-image", "image/jpeg")

    original = app.config["SECRET_KEY"]
    app.config["SECRET_KEY"] = ""
    try:
        response = client.get(f"/image-proxy?token={token}")
        assert response.status_code == 502
    finally:
        app.config["SECRET_KEY"] = original


# ─── End-to-end through the /image-proxy route ──────────────────────────────


def test_proxy_reattaches_credentials_server_side(app, client, session, monkeypatch):
    """The stripped credential must come back as a header on the upstream request.

    This is what keeps artwork rendering after the token is removed from the URL.
    """
    from app.models import MediaServer

    server = MediaServer(
        name="Plex",
        server_type="plex",
        url="http://plex.internal:32400",
        api_key=PLEX_TOKEN,
    )
    session.add(server)
    session.commit()

    ImageProxyService._server_header_cache.clear()

    captured = {}

    class _FakeResponse:
        status_code = 200
        headers: ClassVar = {"Content-Type": "image/jpeg"}
        content = b"\xff\xd8\xff\xe0-jpeg-bytes"

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield self.content

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class _FakeSession:
        def get(self, url, headers=None, timeout=None, **kwargs):
            captured["url"] = url
            captured["headers"] = headers or {}
            captured["kwargs"] = kwargs
            return _FakeResponse()

    monkeypatch.setattr(
        ImageProxyService,
        "get_session",
        classmethod(lambda cls, url, server_id: _FakeSession()),
    )

    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=server.id)

    resp = client.get(f"/image-proxy?token={token}")

    assert resp.status_code == 200
    assert resp.data == _FakeResponse.content

    # The credential was stripped from the URL...
    assert "X-Plex-Token" not in captured["url"]
    assert PLEX_TOKEN not in captured["url"]
    # ...and re-attached as a header from the MediaServer row
    assert captured["headers"].get("X-Plex-Token") == PLEX_TOKEN
    # Hardening: the proxied fetch does not follow redirects.
    assert captured["kwargs"].get("allow_redirects") is False
    # Hardening: upstream-controlled Content-Type on a public, cacheable route
    # must forbid MIME sniffing.
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_proxy_does_not_send_media_credentials_to_foreign_origin(
    app, client, session, monkeypatch
):
    """External artwork may keep its own query auth but gets no media-server key."""
    from app.models import MediaServer

    server = MediaServer(
        name="Audiobookshelf",
        server_type="audiobookshelf",
        url="http://abs.internal:13378",
        api_key="ABS-ADMIN-KEY",
    )
    session.add(server)
    session.commit()

    external_url = "https://cdn.example.com/cover.jpg?token=CDN-SIGNATURE"
    captured = {}

    class _FakeResponse:
        status_code = 200
        headers: ClassVar = {"Content-Type": "image/jpeg"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"image"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class _FakeSession:
        def get(self, url, headers=None, timeout=None, **kwargs):
            captured["url"] = url
            captured["headers"] = headers or {}
            return _FakeResponse()

    monkeypatch.setattr(
        ImageProxyService,
        "get_session",
        classmethod(lambda cls, url, server_id: _FakeSession()),
    )

    with app.app_context():
        token = ImageProxyService.generate_token(external_url, server_id=server.id)

    response = client.get(f"/image-proxy?token={token}")

    assert response.status_code == 200
    assert captured["url"] == external_url
    assert "Authorization" not in captured["headers"]


def test_proxy_reconstructs_configured_basic_auth(app, client, session, monkeypatch):
    """Stripped URL userinfo is restored as server-side Basic authentication."""
    from app.models import MediaServer

    server = MediaServer(
        name="Plex behind Basic Auth",
        server_type="plex",
        url="http://proxy-user:proxy-pass@plex.internal:32400",
        api_key=PLEX_TOKEN,
    )
    session.add(server)
    session.commit()

    upstream_url = (
        "http://proxy-user:proxy-pass@plex.internal:32400/thumb.jpg"
        f"?X-Plex-Token={PLEX_TOKEN}"
    )
    captured = {}

    class _FakeResponse:
        status_code = 200
        headers: ClassVar = {"Content-Type": "image/jpeg"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            yield b"image"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class _FakeSession:
        def get(self, url, headers=None, timeout=None, **kwargs):
            captured["url"] = url
            captured["headers"] = headers or {}
            return _FakeResponse()

    monkeypatch.setattr(
        ImageProxyService,
        "get_session",
        classmethod(lambda cls, url, server_id: _FakeSession()),
    )

    with app.app_context():
        token = ImageProxyService.generate_token(upstream_url, server_id=server.id)

    response = client.get(f"/image-proxy?token={token}")

    assert response.status_code == 200
    assert captured["url"] == "http://plex.internal:32400/thumb.jpg"
    assert captured["headers"]["Authorization"] == (
        "Basic cHJveHktdXNlcjpwcm94eS1wYXNz"
    )
    assert captured["headers"]["X-Plex-Token"] == PLEX_TOKEN


# ─── Movie-poster builders must not leak credentials ────────────────────────
#
# GHSA-gw9v-5c74-gwmr sibling path: the public, unauthenticated /cinema-posters
# route returns get_movie_posters() output verbatim. Plex already proxies these,
# but Jellyfin and Emby previously appended ?api_key=<admin token> to the raw
# URL, disclosing the admin key to anyone — no invite required. Both must now go
# through the opaque image proxy, exactly like Plex.

JELLYFIN_EMBY_ADMIN_KEY = "jf-EmBy-AdM1n-K3y"  # test fixture, not a real credential


class _FakeItemsResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _poster_client(cls):
    """Build a Jellyfin/Emby client without __init__ (no network, no DB)."""
    client = object.__new__(cls)
    client.url = "http://media.internal:8096"
    client.token = JELLYFIN_EMBY_ADMIN_KEY
    client.server_id = 1
    client.get = lambda endpoint, params=None: _FakeItemsResponse(
        {"Items": [{"Id": "movie-1"}, {"Id": "movie-2"}]}
    )
    return client


@pytest.mark.parametrize("cls", [JellyfinClient, EmbyClient])
def test_movie_posters_are_proxied_not_credential_bearing(app, cls):
    """get_movie_posters must emit opaque proxy URLs, never a raw api_key URL."""
    with app.app_context():
        posters = _poster_client(cls).get_movie_posters(limit=10)

    assert posters, "expected at least one poster URL"
    for url in posters:
        # Nothing recoverable by the (possibly anonymous) client...
        assert JELLYFIN_EMBY_ADMIN_KEY not in url
        assert "api_key" not in url.lower()
        # ...and every poster goes through the opaque image proxy.
        assert url.startswith("/image-proxy?token=")

        # Defense in depth: opaque even to a client that decodes the token.
        token = unquote_plus(url.split("token=", 1)[1])
        assert JELLYFIN_EMBY_ADMIN_KEY.encode() not in _decode(token)


@pytest.mark.parametrize("cls", [JellyfinClient, EmbyClient])
def test_movie_posters_query_is_recursive(app, cls):
    """Without Recursive, /Items returns only root folders and no movies, so the
    cinema background is silently empty. Guard that the query descends libraries."""
    captured = {}

    def fake_get(endpoint, params=None):
        captured["params"] = params or {}
        return _FakeItemsResponse({"Items": [{"Id": "movie-1"}]})

    client = _poster_client(cls)
    client.get = fake_get
    with app.app_context():
        client.get_movie_posters(limit=10)

    assert captured["params"].get("Recursive") is True


# ─── Deterministic encryption safety ───────────────────────────────────────


def test_distinct_payloads_produce_distinct_tokens(app):
    """URL and server identity must both be authenticated token inputs."""
    with app.app_context():
        tok_a = ImageProxyService.generate_token(
            "http://plex.internal:32400/library/metadata/1/thumb/1", server_id=1
        )
        ImageProxyService._token_cache.clear()
        tok_b = ImageProxyService.generate_token(
            "http://plex.internal:32400/library/metadata/2/thumb/1", server_id=1
        )
        ImageProxyService._token_cache.clear()
        tok_a_other_server = ImageProxyService.generate_token(
            "http://plex.internal:32400/library/metadata/1/thumb/1", server_id=2
        )

    assert tok_a != tok_b
    assert tok_a != tok_a_other_server


# ─── Host-scoped credential stripping ────────────────────────────────────────


def test_credentials_stripped_only_from_matching_host(app, session):
    from app.models import MediaServer

    server = MediaServer(
        name="Plex",
        server_type="plex",
        url="http://plex.internal:32400",
        api_key="k",
    )
    session.add(server)
    session.commit()

    url = "http://plex.internal:32400/thumb?X-Plex-Token=SECRET&maxWidth=300"
    with app.app_context():
        token = ImageProxyService.generate_token(url, server_id=server.id)
        ImageProxyService._token_cache.clear()
        mapping = ImageProxyService.validate_token(token)

    assert mapping is not None
    assert "SECRET" not in mapping["url"]
    assert "maxWidth=300" in mapping["url"]


def test_credentials_kept_on_foreign_host(app, session):
    """A token/api_key param on an external host (not the media server) may be
    genuinely required, so it must survive; encryption keeps it opaque."""
    from app.models import MediaServer

    server = MediaServer(
        name="ABS",
        server_type="audiobookshelf",
        url="http://abs.internal:13378",
        api_key="abs-key",
    )
    session.add(server)
    session.commit()

    external = "https://cdn.example.com/podcast/cover.jpg?token=SIGNEDCDN&w=1"
    with app.app_context():
        token = ImageProxyService.generate_token(external, server_id=server.id)
        ImageProxyService._token_cache.clear()
        mapping = ImageProxyService.validate_token(token)

    assert mapping is not None
    assert mapping["url"] == external


# ─── Token canonicality & cache bounding ─────────────────────────────────────


def test_non_canonical_token_aliases_rejected(app):
    """urlsafe_b64decode silently drops junk bytes; without canonical-form
    enforcement one valid token spawns unlimited accepted aliases, each its own
    cache key (memory + upstream-fetch amplification on an unauthenticated route)."""
    with app.app_context():
        token = ImageProxyService.generate_token(POSTER_URL, server_id=1)
        ImageProxyService._token_cache.clear()

        # Baseline: the genuine token still validates.
        assert ImageProxyService.validate_token(token) is not None

        # Each alias decodes to the SAME ciphertext but is a different string.
        for alias in (token + "!!!!", "~~~~" + token, token[:6] + "!!!!" + token[6:]):
            ImageProxyService._token_cache.clear()
            assert ImageProxyService.validate_token(alias) is None


def test_token_cache_is_bounded(app):
    with app.app_context():
        for i in range(ImageProxyService.TOKEN_CACHE_MAX_ENTRIES + 50):
            ImageProxyService.generate_token(
                f"http://plex.internal:32400/thumb/{i}", server_id=1
            )

    assert (
        len(ImageProxyService._token_cache) <= ImageProxyService.TOKEN_CACHE_MAX_ENTRIES
    )


# ─── Per-server-type header re-attachment ────────────────────────────────────


@pytest.mark.parametrize(
    "server_type,header_name,expected",
    [
        ("plex", "X-Plex-Token", "THE-KEY"),
        ("jellyfin", "X-MediaBrowser-Token", "THE-KEY"),
        ("emby", "X-Emby-Token", "THE-KEY"),
        ("komga", "X-API-Key", "THE-KEY"),
        ("audiobookshelf", "Authorization", "Bearer THE-KEY"),
    ],
)
def test_get_server_headers_per_type(app, session, server_type, header_name, expected):
    from app.models import MediaServer

    server = MediaServer(
        name=server_type,
        server_type=server_type,
        url="http://media.internal",
        api_key="THE-KEY",
    )
    session.add(server)
    session.commit()

    with app.app_context():
        headers = ImageProxyService.get_server_headers(server.id, server.url)

    assert headers.get(header_name) == expected


def test_get_server_headers_unknown_type_is_empty(app, session):
    from app.models import MediaServer

    server = MediaServer(
        name="other",
        server_type="navidrome",
        url="http://other.internal",
        api_key="THE-KEY",
    )
    session.add(server)
    session.commit()

    with app.app_context():
        headers = ImageProxyService.get_server_headers(server.id, server.url)

    assert headers == {}


# ─── Hardening: fail-closed secret, no redirects, response-size cap ──────────


def test_missing_secret_key_fails_closed(app):
    """With no SECRET_KEY the token is neither opaque nor unforgeable, so token
    generation must raise rather than fall back to a public constant."""
    original = app.config["SECRET_KEY"]
    app.config["SECRET_KEY"] = ""
    try:
        with app.app_context(), pytest.raises(RuntimeError):
            ImageProxyService.generate_token(
                "http://plex.internal:32400/thumb.jpg", server_id=1
            )
    finally:
        app.config["SECRET_KEY"] = original


def _poster_server(session):
    from app.models import MediaServer

    server = MediaServer(
        name="Plex",
        server_type="plex",
        url="http://plex.internal:32400",
        api_key=PLEX_TOKEN,
    )
    session.add(server)
    session.commit()
    return server


def test_proxy_rejects_oversize_upstream(app, client, session, monkeypatch):
    """A body over the hard cap must be abandoned mid-stream (not fully
    buffered), the connection released, and redirects must not be followed."""
    server = _poster_server(session)

    monkeypatch.setattr(ImageProxyService, "IMAGE_PROXY_MAX_BYTES", 32)
    events = {"pulled": 0, "closed": False}
    captured = {}

    class _BigResponse:
        status_code = 200
        headers: ClassVar = CaseInsensitiveDict({"Content-Type": "image/jpeg"})

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            for _ in range(1000):  # far more than the 32-byte cap allows
                events["pulled"] += 1
                yield b"\x00" * 16

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            events["closed"] = True
            return False

    class _BigSession:
        def get(self, url, headers=None, timeout=None, **kwargs):
            captured["kwargs"] = kwargs
            return _BigResponse()

    monkeypatch.setattr(
        ImageProxyService,
        "get_session",
        classmethod(lambda cls, url, server_id: _BigSession()),
    )

    with app.app_context():
        token = ImageProxyService.generate_token(
            "http://plex.internal:32400/thumb.jpg", server_id=server.id
        )

    resp = client.get(f"/image-proxy?token={token}")

    assert resp.status_code == 502
    assert events["pulled"] < 10  # aborted mid-stream, not fully buffered
    assert events["closed"] is True  # context manager released the connection
    assert captured["kwargs"].get("allow_redirects") is False
    assert captured["kwargs"].get("stream") is True


def test_proxy_does_not_follow_redirects(app, client, session, monkeypatch):
    """An unfollowed 3xx becomes a 502; the redirect body is never read/served."""
    server = _poster_server(session)
    served = {"body": False}

    class _RedirectResponse:
        status_code = 302
        headers: ClassVar = CaseInsensitiveDict(
            {"Content-Type": "text/html", "Location": "http://evil.example/"}
        )

        def raise_for_status(self):
            return None  # requests does not raise on 3xx

        def iter_content(self, chunk_size):
            served["body"] = True
            yield b"redirect-body"

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(
        ImageProxyService,
        "get_session",
        classmethod(
            lambda cls, url, server_id: type(
                "_S", (), {"get": lambda s, *a, **k: _RedirectResponse()}
            )()
        ),
    )

    with app.app_context():
        token = ImageProxyService.generate_token(
            "http://plex.internal:32400/thumb.jpg", server_id=server.id
        )

    resp = client.get(f"/image-proxy?token={token}")

    assert resp.status_code == 502
    assert served["body"] is False


def test_proxy_rejects_oversize_content_length(app, client, session, monkeypatch):
    """An honest over-cap Content-Length is refused before the body is read."""
    server = _poster_server(session)
    monkeypatch.setattr(ImageProxyService, "IMAGE_PROXY_MAX_BYTES", 100)
    events = {"pulled": 0}

    class _ClResponse:
        status_code = 200
        headers: ClassVar = CaseInsensitiveDict(
            {"Content-Type": "image/jpeg", "Content-Length": "500"}
        )

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            events["pulled"] += 1
            yield b"\x00" * 16

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(
        ImageProxyService,
        "get_session",
        classmethod(
            lambda cls, url, server_id: type(
                "_S", (), {"get": lambda s, *a, **k: _ClResponse()}
            )()
        ),
    )

    with app.app_context():
        token = ImageProxyService.generate_token(
            "http://plex.internal:32400/thumb.jpg", server_id=server.id
        )

    resp = client.get(f"/image-proxy?token={token}")

    assert resp.status_code == 502
    assert events["pulled"] == 0  # rejected on Content-Length before reading body
