"""
Secure image proxy service with opaque token-based access.

This prevents SSRF attacks by not exposing the underlying URL to clients.
Instead, we generate signed tokens that map to internal URLs.
"""

import base64
import hashlib
import hmac
import json
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
        hour_bucket = int(current_time / 3600)

        # Create payload with URL, server_id, and expiry info
        payload = {
            "url": url,
            "server_id": server_id,
            "bucket": hour_bucket,
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
        cls._token_cache[token] = {
            "url": url,
            "timestamp": current_time,
            "server_id": server_id,
        }

        # Clean up old tokens
        cls._cleanup_token_cache()

        return token

    @classmethod
    def validate_token(cls, token: str) -> dict | None:
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

        # Verify token hasn't expired (allow current hour bucket + previous hour)
        current_bucket = int(time.time() / 3600)
        token_bucket = payload.get("bucket")

        if token_bucket is None or current_bucket - token_bucket > 1:
            return None

        # Cache the validated token for future requests
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
