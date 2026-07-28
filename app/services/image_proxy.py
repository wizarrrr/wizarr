"""
Secure image proxy service with opaque token-based access.

This prevents SSRF attacks by not exposing the underlying URL to clients.
The upstream URL is encrypted with a key derived from SECRET_KEY, so the token
handed to the browser is genuinely opaque rather than merely encoded.
"""

import base64
import hashlib
import json
import threading
import time
from collections import OrderedDict
from collections.abc import Hashable
from typing import Any, ClassVar
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlsplit, urlunsplit

import requests
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from flask import current_app
from requests.adapters import HTTPAdapter


class ImageProxyService:
    """Service for generating and validating opaque image proxy tokens."""

    # In-memory cache for URL -> token mappings
    _token_cache: ClassVar[dict[str, dict]] = {}

    # Cache for image data (in-memory LRU with byte and count limits)
    _image_cache: ClassVar[OrderedDict[str, dict[str, Any]]] = OrderedDict()
    _image_cache_lock: ClassVar[threading.Lock] = threading.Lock()
    _total_image_bytes: ClassVar[int] = 0

    # Cache for auth headers per media server
    _server_header_cache: ClassVar[dict[int, dict[str, Any]]] = {}
    _server_header_cache_lock: ClassVar[threading.Lock] = threading.Lock()

    # Connection pool per server/host
    _session_cache: ClassVar[OrderedDict[Hashable, dict[str, Any]]] = OrderedDict()
    _session_cache_lock: ClassVar[threading.Lock] = threading.Lock()

    TOKEN_EXPIRY = 24 * 3600  # Tokens remain valid for 24 hours
    TOKEN_BUCKET_SECONDS = 3600  # Bucket tokens hourly to keep payload compact
    TOKEN_CACHE_MAX_ENTRIES = 512  # Backstop against unbounded token-cache growth
    IMAGE_CACHE_EXPIRY = 3600  # 1 hour
    IMAGE_CACHE_MAX_ENTRIES = 300
    IMAGE_CACHE_MAX_BYTES = 20 * 1024 * 1024  # 20 MB
    IMAGE_CACHE_MAX_SINGLE_BYTES = 4 * 1024 * 1024  # Skip caching images >4 MB
    IMAGE_PROXY_MAX_BYTES = 25 * 1024 * 1024  # Hard cap on a single upstream fetch
    SERVER_HEADER_TTL = 300  # 5 minutes
    SESSION_CACHE_MAX_ENTRIES = 12

    # Query parameters that carry media-server credentials. plexapi's
    # ``posterUrl`` (and the Jellyfin/Emby/Komga equivalents) return
    # fully-authenticated artwork URLs, so the admin token routinely ends up in
    # the URL we are handed. The proxy re-attaches the correct header from the
    # MediaServer row at fetch time, so these are redundant here.
    CREDENTIAL_QUERY_PARAMS: ClassVar[frozenset[str]] = frozenset(
        {
            "x-plex-token",
            "x-emby-token",
            "x-mediabrowser-token",
            "x-api-key",
            "api_key",
            "apikey",
            "token",
        }
    )

    _token_cache_lock = threading.Lock()

    # Derived key, memoised per secret
    _cipher_key_cache: ClassVar[dict[bytes, bytes]] = {}
    _cipher_key_lock: ClassVar[threading.Lock] = threading.Lock()

    # Cache for media-server origins, used to scope credentials to their server
    _server_url_cache: ClassVar[dict[int, dict[str, Any]]] = {}
    _server_url_cache_lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def _get_secret(cls) -> bytes:
        """Return SECRET_KEY as bytes, failing closed if it is unset.

        The token is only opaque and unforgeable while SECRET_KEY is secret, so
        refuse to operate on a missing/empty key rather than fall back to a
        publicly known constant (which would re-enable decryption and forgery).
        """
        secret = current_app.config.get("SECRET_KEY")
        if not secret:
            raise RuntimeError("SECRET_KEY is not configured")
        return secret.encode() if isinstance(secret, str) else secret

    @classmethod
    def _cipher_key(cls) -> bytes:
        """Derive a 512-bit AES-SIV key from SECRET_KEY.

        Domain-separated so the image-proxy key can never collide with any other
        use of SECRET_KEY (Flask session cookies, etc.).
        """
        secret = cls._get_secret()

        with cls._cipher_key_lock:
            cached = cls._cipher_key_cache.get(secret)
            if cached is not None:
                return cached

            key = hashlib.sha512(b"wizarr.image-proxy.aes-siv.v1\x00" + secret).digest()
            cls._cipher_key_cache[secret] = key
            return key

    @staticmethod
    def _canonical_origin(url: str) -> tuple[str, str, int] | None:
        """Return ``(scheme, hostname, port)`` for an HTTP(S) URL."""
        try:
            parsed = urlsplit(url)
            scheme = parsed.scheme.lower()
            if scheme not in {"http", "https"} or parsed.hostname is None:
                return None
            port = parsed.port or (443 if scheme == "https" else 80)
        except ValueError:
            return None
        return (scheme, parsed.hostname.lower(), port)

    @classmethod
    def _server_origin(cls, server_id: int) -> tuple[str, str, int] | None:
        """Return the media server's canonical origin, cached when available.

        Credentials may only be removed from, or attached to, requests targeting
        this exact origin. Matching the scheme and effective port as well as the
        hostname prevents a key intended for one service reaching another
        service on the same host.
        """
        now = time.time()
        with cls._server_url_cache_lock:
            cached = cls._server_url_cache.get(server_id)
            if cached and (now - cached["timestamp"] < cls.SERVER_HEADER_TTL):
                return cached["origin"]

        from app.extensions import db
        from app.models import MediaServer  # Local import to avoid circulars

        server = db.session.get(MediaServer, server_id)
        origin = cls._canonical_origin(server.url) if server and server.url else None

        with cls._server_url_cache_lock:
            cls._server_url_cache[server_id] = {
                "origin": origin,
                "timestamp": now,
            }

        return origin

    @classmethod
    def _strip_credentials(
        cls, url: str, server_origin: tuple[str, str, int] | None = None
    ) -> str:
        """Remove embedded credentials from an upstream image URL.

        Only called when we have a ``server_id``, because the proxy can then
        re-attach the correct auth header from the MediaServer row at fetch time
        (see :meth:`get_server_headers`). Without a ``server_id`` the URL is the
        only way to authenticate, so it is left intact and protected solely by
        the payload encryption.

        Stripping is origin-scoped. A param named ``token`` or ``api_key`` on a
        foreign origin (e.g. a podcast cover served from a CDN) may be genuinely
        required and cannot be reconstructed from the MediaServer row, so it is
        left for the encryption layer to keep opaque.
        """
        try:
            parsed = urlsplit(url)
        except ValueError:
            return url

        # Only touch URLs that point at the media server itself.
        if server_origin is None or cls._canonical_origin(url) != server_origin:
            return url

        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        cleaned = [
            (key, value)
            for key, value in pairs
            if key.lower() not in cls.CREDENTIAL_QUERY_PARAMS
        ]

        # Drop any ``user:pass@`` userinfo as well
        netloc = parsed.netloc
        if "@" in netloc:
            netloc = netloc.rsplit("@", 1)[1]

        if len(cleaned) == len(pairs) and netloc == parsed.netloc:
            return url

        return urlunsplit(
            (parsed.scheme, netloc, parsed.path, urlencode(cleaned), parsed.fragment)
        )

    @classmethod
    def _bucket_within_expiry(cls, token_bucket: int | None) -> bool:
        """Whether a token minted in ``token_bucket`` is still inside TOKEN_EXPIRY.

        Single source of truth for token freshness, used by both the fast
        token-cache path and the decrypt path. Deriving expiry from the token's
        own bucket (not the cache insertion time) stops a token that is
        re-validated and re-cached near end of life from having its lifetime
        silently extended by another TOKEN_EXPIRY.
        """
        if token_bucket is None:
            return False
        bucket_diff = int(time.time() / cls.TOKEN_BUCKET_SECONDS) - token_bucket
        if bucket_diff < 0:
            return False
        return bucket_diff * cls.TOKEN_BUCKET_SECONDS < cls.TOKEN_EXPIRY

    @classmethod
    def generate_token(cls, url: str, server_id: int | None = None) -> str:
        """
        Generate a stateless encrypted token for an image URL.

        The token embeds the URL and server_id, encrypted with AES-SIV under a
        key derived from SECRET_KEY. AES-SIV authenticates as well as encrypts,
        so the token is both tamper-proof and opaque to the client. Being
        stateless, it works across multiple workers without shared state.

        Args:
            url: The internal/media server URL to proxy
            server_id: Optional media server ID for authentication

        Returns:
            Opaque token that can be used with /image-proxy?token=...
        """
        current_time = time.time()
        bucket = int(current_time / cls.TOKEN_BUCKET_SECONDS)

        # Never carry credentials we are able to reconstruct server-side. Scope
        # stripping to the media server's own host so foreign artwork URLs keep
        # any param they legitimately need.
        if server_id is not None:
            url = cls._strip_credentials(url, cls._server_origin(server_id))

        # Create payload with URL, server_id, and expiry info
        payload = {
            "url": url,
            "server_id": server_id,
            "bucket": bucket,
        }

        payload_json = json.dumps(payload, separators=(",", ":")).encode()

        # AES-SIV is deterministic and misuse-resistant by construction.
        # Identical payloads therefore produce identical tokens, which keeps the
        # token and image caches effective across renders, users, and workers.
        cipher_key = cls._cipher_key()
        ciphertext = AESSIV(cipher_key).encrypt(payload_json, None)
        token = base64.urlsafe_b64encode(ciphertext).decode().rstrip("=")

        # Also store in cache for faster lookups (optional optimization)
        with cls._token_cache_lock:
            cls._token_cache[token] = {
                "url": url,
                "timestamp": current_time,
                "server_id": server_id,
                "bucket": bucket,
                "cipher_key": cipher_key,
            }
            cls._cleanup_token_cache_locked()

        return token

    @classmethod
    def validate_token(cls, token: str) -> dict | None:
        """
        Validate a stateless encrypted token and return the URL mapping.

        Args:
            token: The token to validate (base64url of AES-SIV ciphertext)

        Returns:
            Dict with 'url' and 'server_id' if valid, None otherwise
        """
        if not token:
            return None

        # Fail closed before consulting caches, and bind every cached mapping to
        # the key that authenticated it. Otherwise a hot cache could keep serving
        # after SECRET_KEY was removed or rotated.
        cipher_key = cls._cipher_key()

        # Check cache first for performance (optional optimization). Expiry is
        # judged from the token's own bucket, not the cache insertion time, so a
        # cached entry can never outlive the token it stands in for.
        with cls._token_cache_lock:
            cached_mapping = cls._token_cache.get(token)
        if (
            cached_mapping
            and cached_mapping.get("cipher_key") == cipher_key
            and cls._bucket_within_expiry(cached_mapping.get("bucket"))
        ):
            return {
                "url": cached_mapping["url"],
                "server_id": cached_mapping.get("server_id"),
            }

        # Decrypt payload. AES-SIV rejects any tampering via its auth tag, so a
        # separate signature check is unnecessary.
        try:
            padding = (4 - len(token) % 4) % 4
            raw = base64.urlsafe_b64decode(token + ("=" * padding))
        except (ValueError, TypeError):
            return None

        # Reject non-canonical encodings. urlsafe_b64decode silently drops any
        # non-alphabet bytes, so without this an attacker could splice junk into
        # a valid token to mint unlimited distinct strings that all decrypt the
        # same, each becoming its own _token_cache / _image_cache key.
        if base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != token:
            return None

        if len(raw) <= 16:  # AES-SIV authentication tag plus non-empty payload
            return None

        try:
            payload_json = AESSIV(cipher_key).decrypt(raw, None)
            payload = json.loads(payload_json)
        except (InvalidTag, ValueError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict) or "url" not in payload:
            return None

        # Verify token hasn't expired within the allowed validity window
        if not cls._bucket_within_expiry(payload.get("bucket")):
            return None

        # Cache the validated token for future requests
        with cls._token_cache_lock:
            cls._token_cache[token] = {
                "url": payload["url"],
                "timestamp": time.time(),
                "server_id": payload.get("server_id"),
                "bucket": payload.get("bucket"),
                "cipher_key": cipher_key,
            }
            cls._cleanup_token_cache_locked()

        return {"url": payload["url"], "server_id": payload.get("server_id")}

    @classmethod
    def get_cached_image(cls, token: str) -> dict | None:
        """
        Get cached image data for a token.

        Returns:
            Dict with 'data' and 'content_type' if cached, None otherwise
        """
        with cls._image_cache_lock:
            cached = cls._image_cache.get(token)
            if not cached:
                return None

            # Check expiry
            if time.time() - cached["timestamp"] > cls.IMAGE_CACHE_EXPIRY:
                cls._evict_image_locked(token)
                return None

            # Move to end to mark as recently used
            cls._image_cache.move_to_end(token)

            return {
                "data": cached["data"],
                "content_type": cached["content_type"],
            }

    @classmethod
    def cache_image(cls, token: str, data: bytes, content_type: str) -> None:
        """Cache image data for a token."""
        image_size = len(data)
        if image_size > cls.IMAGE_CACHE_MAX_SINGLE_BYTES:
            return

        with cls._image_cache_lock:
            existing = cls._image_cache.pop(token, None)
            if existing:
                cls._total_image_bytes -= existing.get("size", 0)
                cls._total_image_bytes = max(cls._total_image_bytes, 0)

            cls._image_cache[token] = {
                "data": data,
                "content_type": content_type,
                "timestamp": time.time(),
                "size": image_size,
            }
            cls._image_cache.move_to_end(token)
            cls._total_image_bytes += image_size
            cls._enforce_image_cache_limits_locked()

    @classmethod
    def get_server_headers(
        cls, server_id: int | None, target_url: str
    ) -> dict[str, str]:
        """Return media-server auth headers only for that server's origin."""
        if not server_id or cls._canonical_origin(target_url) != cls._server_origin(
            server_id
        ):
            return {}

        now = time.time()
        with cls._server_header_cache_lock:
            cached = cls._server_header_cache.get(server_id)
            if cached and (now - cached["timestamp"] < cls.SERVER_HEADER_TTL):
                return cached["headers"]

        from app.extensions import db
        from app.models import MediaServer  # Local import to avoid circulars

        server = db.session.get(MediaServer, server_id)
        headers: dict[str, str] = {}
        if server and server.api_key:
            if server.server_type == "audiobookshelf":
                headers["Authorization"] = f"Bearer {server.api_key}"
            elif server.server_type == "jellyfin":
                headers["X-MediaBrowser-Token"] = server.api_key
            elif server.server_type == "emby":
                headers["X-Emby-Token"] = server.api_key
            elif server.server_type == "plex":
                headers["X-Plex-Token"] = server.api_key
            elif server.server_type == "komga":
                headers["X-API-Key"] = server.api_key

        # Requests normally converts URL userinfo into Basic authentication.
        # Because generate_token() removes that userinfo from the upstream URL,
        # reconstruct the same header from the trusted MediaServer row. This is
        # still safe because the method returns early for every foreign origin.
        if server and server.url:
            configured_url = urlsplit(server.url)
            if configured_url.username is not None:
                username = unquote(configured_url.username)
                password = unquote(configured_url.password or "")
                credentials = base64.b64encode(
                    f"{username}:{password}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {credentials}"

        with cls._server_header_cache_lock:
            cls._server_header_cache[server_id] = {
                "headers": headers,
                "timestamp": now,
            }

        return headers

    @classmethod
    def get_session(cls, url: str, server_id: int | None) -> requests.Session:
        """Return a pooled requests Session keyed by server_id/host."""
        cache_key = cls._session_cache_key(url, server_id)

        with cls._session_cache_lock:
            entry = cls._session_cache.get(cache_key)
            if entry:
                entry["last_used"] = time.time()
                cls._session_cache.move_to_end(cache_key)
                return entry["session"]

            session = requests.Session()
            adapter = HTTPAdapter(pool_connections=4, pool_maxsize=8)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            cls._session_cache[cache_key] = {
                "session": session,
                "last_used": time.time(),
            }
            cls._session_cache.move_to_end(cache_key)
            cls._trim_session_cache_locked()
            return session

    @classmethod
    def _session_cache_key(
        cls, url: str, server_id: int | None
    ) -> tuple[str, Hashable]:
        if server_id:
            return ("server", server_id)

        parsed = urlparse(url)
        host = (parsed.scheme or "http", parsed.netloc)
        return ("host", host)

    @classmethod
    def _trim_session_cache_locked(cls) -> None:
        """Ensure we do not keep more sessions than required."""
        while len(cls._session_cache) > cls.SESSION_CACHE_MAX_ENTRIES:
            _key, entry = cls._session_cache.popitem(last=False)
            session = entry.get("session")
            if session:
                session.close()

    @classmethod
    def _cleanup_token_cache_locked(cls) -> None:
        """Remove expired tokens, then bound the cache size."""
        current_time = time.time()
        expired = [
            token
            for token, mapping in cls._token_cache.items()
            if current_time - mapping["timestamp"] > cls.TOKEN_EXPIRY
        ]
        for token in expired:
            del cls._token_cache[token]

        # Hard cap as a backstop against unbounded growth (dict preserves
        # insertion order, so this evicts oldest-first).
        while len(cls._token_cache) > cls.TOKEN_CACHE_MAX_ENTRIES:
            del cls._token_cache[next(iter(cls._token_cache))]

    @classmethod
    def _evict_image_locked(cls, token: str) -> None:
        """Remove image cache entry and update counters (expects lock held)."""
        cached = cls._image_cache.pop(token, None)
        if cached:
            cls._total_image_bytes -= cached.get("size", 0)
            cls._total_image_bytes = max(cls._total_image_bytes, 0)

    @classmethod
    def _enforce_image_cache_limits_locked(cls) -> None:
        """Evict old images until count and byte limits are satisfied."""
        current_time = time.time()

        # Remove expired entries first
        expired_tokens = [
            token
            for token, details in cls._image_cache.items()
            if current_time - details["timestamp"] > cls.IMAGE_CACHE_EXPIRY
        ]
        for token in expired_tokens:
            cls._evict_image_locked(token)

        # Enforce entry count
        while len(cls._image_cache) > cls.IMAGE_CACHE_MAX_ENTRIES:
            oldest_token = next(iter(cls._image_cache))
            cls._evict_image_locked(oldest_token)

        # Enforce byte size
        while cls._total_image_bytes > cls.IMAGE_CACHE_MAX_BYTES and cls._image_cache:
            oldest_token = next(iter(cls._image_cache))
            cls._evict_image_locked(oldest_token)
