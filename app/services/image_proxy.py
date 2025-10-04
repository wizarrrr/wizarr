"""
Secure image proxy service with opaque token-based access.

This prevents SSRF attacks by not exposing the underlying URL to clients.
Instead, we generate signed tokens that map to internal URLs.
"""

import hashlib
import hmac
import time

from flask import current_app


class ImageProxyService:
    """Service for generating and validating opaque image proxy tokens."""

    # In-memory cache for URL -> token mappings
    # Structure: {token: {"url": str, "timestamp": float, "server_id": int}}
    _token_cache: dict[str, dict] = {}

    # Cache for image data
    # Structure: {token: {"data": bytes, "content_type": str, "timestamp": float}}
    _image_cache: dict[str, dict] = {}

    TOKEN_EXPIRY = 3600  # 1 hour
    IMAGE_CACHE_EXPIRY = 3600  # 1 hour
    MAX_CACHE_SIZE = 200  # Max number of cached images

    @classmethod
    def _get_secret(cls) -> bytes:
        """Get the secret key for signing tokens."""
        secret = current_app.config.get("SECRET_KEY", "wizarr-dev-secret")
        return secret.encode() if isinstance(secret, str) else secret

    @classmethod
    def generate_token(cls, url: str, server_id: int | None = None) -> str:
        """
        Generate an opaque token for an image URL.

        Args:
            url: The internal/media server URL to proxy
            server_id: Optional media server ID for authentication

        Returns:
            Opaque token that can be used with /image-proxy?token=...
        """
        # Create a deterministic token based on URL and timestamp (hour bucket)
        # This allows the same URL to reuse tokens within the same hour
        hour_bucket = int(time.time() / 3600)
        data = f"{url}:{hour_bucket}".encode()

        # Generate HMAC signature
        signature = hmac.new(cls._get_secret(), data, hashlib.sha256).hexdigest()

        # Use first 32 chars of signature as token (128 bits of entropy)
        token = signature[:32]

        # Store mapping in cache
        cls._token_cache[token] = {
            "url": url,
            "timestamp": time.time(),
            "server_id": server_id,
        }

        # Clean up old tokens
        cls._cleanup_token_cache()

        return token

    @classmethod
    def validate_token(cls, token: str) -> dict | None:
        """
        Validate a token and return the URL mapping.

        Args:
            token: The opaque token to validate

        Returns:
            Dict with 'url' and 'server_id' if valid, None otherwise
        """
        if not token or len(token) != 32:
            return None

        # Check cache
        mapping = cls._token_cache.get(token)
        if not mapping:
            return None

        # Check expiry
        if time.time() - mapping["timestamp"] > cls.TOKEN_EXPIRY:
            del cls._token_cache[token]
            return None

        return {"url": mapping["url"], "server_id": mapping.get("server_id")}

    @classmethod
    def get_cached_image(cls, token: str) -> dict | None:
        """
        Get cached image data for a token.

        Returns:
            Dict with 'data' and 'content_type' if cached, None otherwise
        """
        cached = cls._image_cache.get(token)
        if not cached:
            return None

        # Check expiry
        if time.time() - cached["timestamp"] > cls.IMAGE_CACHE_EXPIRY:
            del cls._image_cache[token]
            return None

        return {"data": cached["data"], "content_type": cached["content_type"]}

    @classmethod
    def cache_image(cls, token: str, data: bytes, content_type: str) -> None:
        """Cache image data for a token."""
        cls._image_cache[token] = {
            "data": data,
            "content_type": content_type,
            "timestamp": time.time(),
        }

        # Clean up old cache entries (simple LRU)
        if len(cls._image_cache) > cls.MAX_CACHE_SIZE:
            oldest_token = min(
                cls._image_cache.keys(),
                key=lambda k: cls._image_cache[k]["timestamp"],
            )
            del cls._image_cache[oldest_token]

    @classmethod
    def _cleanup_token_cache(cls) -> None:
        """Remove expired tokens from cache."""
        current_time = time.time()
        expired = [
            token
            for token, mapping in cls._token_cache.items()
            if current_time - mapping["timestamp"] > cls.TOKEN_EXPIRY
        ]
        for token in expired:
            del cls._token_cache[token]
