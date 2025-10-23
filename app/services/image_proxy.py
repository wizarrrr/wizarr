"""
Secure image proxy service with opaque token-based access.

This prevents SSRF attacks by not exposing the underlying URL to clients.
Instead, we generate signed tokens that map to internal URLs.
"""

import base64
import hashlib
import hmac
import json
import threading
import time
from collections import OrderedDict
from collections.abc import Hashable
from typing import Any, ClassVar
from urllib.parse import urlparse

import requests
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
    IMAGE_CACHE_EXPIRY = 3600  # 1 hour
    IMAGE_CACHE_MAX_ENTRIES = 300
    IMAGE_CACHE_MAX_BYTES = 20 * 1024 * 1024  # 20 MB
    IMAGE_CACHE_MAX_SINGLE_BYTES = 4 * 1024 * 1024  # Skip caching images >4 MB
    SERVER_HEADER_TTL = 300  # 5 minutes
    SESSION_CACHE_MAX_ENTRIES = 12

    _token_cache_lock = threading.Lock()

    @classmethod
    def _get_secret(cls) -> bytes:
        """Get the secret key for signing tokens."""
        secret = current_app.config.get("SECRET_KEY", "wizarr-dev-secret")
        return secret.encode() if isinstance(secret, str) else secret

    @classmethod
    def generate_token(cls, url: str, server_id: int | None = None) -> str:
        """
        Generate a stateless signed token for an image URL.

        The token embeds the URL and server_id, signed with HMAC to prevent tampering.
        This makes tokens work across multiple workers without shared state.

        Args:
            url: The internal/media server URL to proxy
            server_id: Optional media server ID for authentication

        Returns:
            Opaque token that can be used with /image-proxy?token=...
        """
        current_time = time.time()
        bucket = int(current_time / cls.TOKEN_BUCKET_SECONDS)

        # Create payload with URL, server_id, and expiry info
        payload = {
            "url": url,
            "server_id": server_id,
            "bucket": bucket,
        }

        # Encode payload as JSON then base64
        payload_json = json.dumps(payload, separators=(",", ":"))
        payload_b64 = (
            base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
        )

        # Generate HMAC signature over the payload
        signature = hmac.new(
            cls._get_secret(), payload_b64.encode(), hashlib.sha256
        ).hexdigest()[:16]  # Use 16 chars (64 bits) for compactness

        # Token format: signature.payload
        token = f"{signature}.{payload_b64}"

        # Also store in cache for faster lookups (optional optimization)
        with cls._token_cache_lock:
            cls._token_cache[token] = {
                "url": url,
                "timestamp": current_time,
                "server_id": server_id,
            }
            cls._cleanup_token_cache_locked()

        return token

    @classmethod
    def validate_token(cls, token: str) -> dict | None:  # noqa: PLR0911
        """
        Validate a stateless signed token and return the URL mapping.

        Args:
            token: The signed token to validate (format: signature.payload)

        Returns:
            Dict with 'url' and 'server_id' if valid, None otherwise
        """
        if not token:
            return None

        # Check cache first for performance (optional optimization)
        with cls._token_cache_lock:
            cached_mapping = cls._token_cache.get(token)
        if cached_mapping:
            current_time = time.time()
            if current_time - cached_mapping["timestamp"] < cls.TOKEN_EXPIRY:
                return {
                    "url": cached_mapping["url"],
                    "server_id": cached_mapping.get("server_id"),
                }

        # Parse token (signature.payload format)
        parts = token.split(".", 1)
        if len(parts) != 2:
            return None

        signature, payload_b64 = parts

        # Verify HMAC signature
        expected_sig = hmac.new(
            cls._get_secret(), payload_b64.encode(), hashlib.sha256
        ).hexdigest()[:16]

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Decode payload
        try:
            # Add back padding if needed
            padding = (4 - len(payload_b64) % 4) % 4
            payload_b64_padded = payload_b64 + ("=" * padding)
            payload_json = base64.urlsafe_b64decode(payload_b64_padded).decode()
            payload = json.loads(payload_json)
        except (ValueError, json.JSONDecodeError):
            return None

        # Verify token hasn't expired within the allowed validity window
        current_bucket = int(time.time() / cls.TOKEN_BUCKET_SECONDS)
        token_bucket = payload.get("bucket")

        if token_bucket is None:
            return None

        bucket_diff = current_bucket - token_bucket
        if bucket_diff < 0:
            return None

        if bucket_diff * cls.TOKEN_BUCKET_SECONDS > cls.TOKEN_EXPIRY:
            return None

        # Cache the validated token for future requests
        with cls._token_cache_lock:
            cls._token_cache[token] = {
                "url": payload["url"],
                "timestamp": time.time(),
                "server_id": payload.get("server_id"),
            }

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
    def get_server_headers(cls, server_id: int | None) -> dict[str, str]:
        """Return cached auth headers for a media server."""
        if not server_id:
            return {}

        now = time.time()
        with cls._server_header_cache_lock:
            cached = cls._server_header_cache.get(server_id)
            if cached and (now - cached["timestamp"] < cls.SERVER_HEADER_TTL):
                return cached["headers"]

        from app.models import MediaServer  # Local import to avoid circulars

        server = MediaServer.query.get(server_id)
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
        """Remove expired tokens from cache."""
        current_time = time.time()
        expired = [
            token
            for token, mapping in cls._token_cache.items()
            if current_time - mapping["timestamp"] > cls.TOKEN_EXPIRY
        ]
        for token in expired:
            del cls._token_cache[token]

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
