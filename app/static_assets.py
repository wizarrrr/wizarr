"""Versioned URLs, cache headers and compression for static files.

``url_for('static', filename=...)`` adds ``v=<content hash>`` to each URL.
A request with the correct hash gets a one-year ``immutable`` cache header,
because a new file content gives a new URL. A request without a hash (or
with an old hash) keeps the Flask default: ``no-cache`` with revalidation.

Static requests also skip the server-side session. They do not need it, and
this removes a session file read, a session file write and a ``Set-Cookie``
from each static response.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from cachelib import SimpleCache
from flask import Flask, current_app, request
from flask.sessions import SecureCookieSession
from werkzeug.security import safe_join

STATIC_HASHES_EXTENSION = "wizarr_static_hashes"
IMMUTABLE_MAX_AGE = 365 * 24 * 60 * 60
HASH_LENGTH = 12


class StaticFileHashes:
    """Compute a short content hash per static file and keep it in memory."""

    def __init__(self, static_folder: str):
        self.static_folder = static_folder
        self._hashes: dict[str, tuple[int, int, str]] = {}

    def get(self, filename: str, *, check_changes: bool = False) -> str | None:
        """Return the hash of *filename*, or None when the file does not exist.

        With *check_changes*, compare the file size and time of change with
        the cached values (development). Otherwise compute the hash one time.
        """
        cached = self._hashes.get(filename)
        if cached is not None and not check_changes:
            return cached[2]

        joined = safe_join(self.static_folder, filename)
        if joined is None:
            return None
        path = Path(joined)
        try:
            stat = path.stat()
        except OSError:
            return None
        if cached is not None and cached[:2] == (stat.st_mtime_ns, stat.st_size):
            return cached[2]

        try:
            with path.open("rb") as file:
                digest = hashlib.file_digest(file, "sha256").hexdigest()
        except OSError:
            return None

        value = digest[:HASH_LENGTH]
        self._hashes[filename] = (stat.st_mtime_ns, stat.st_size, value)
        return value


def static_file_hash(filename: str, app: Flask | None = None) -> str | None:
    """Return the content hash of a static file for the current app."""
    target = app if app is not None else current_app
    hashes: StaticFileHashes | None = target.extensions.get(STATIC_HASHES_EXTENSION)
    if hashes is None:
        return None
    check_changes = target.debug or bool(target.config.get("TEMPLATES_AUTO_RELOAD"))
    return hashes.get(filename, check_changes=check_changes)


class StaticRequestSession(SecureCookieSession):
    """Empty session for a static request. The app never saves it."""


class StaticSkippingSessionInterface:
    """Wrap the session interface and skip the session for static files."""

    def __init__(self, inner, static_url_path: str):
        self._inner = inner
        self._prefix = static_url_path.rstrip("/") + "/"

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def _is_static(self, req) -> bool:
        return req.path.startswith(self._prefix)

    def open_session(self, app, req):
        if self._is_static(req):
            return StaticRequestSession()
        return self._inner.open_session(app, req)

    def save_session(self, app, session, response):
        if isinstance(session, StaticRequestSession):
            return None
        return self._inner.save_session(app, session, response)


def static_request_filename(req) -> str | None:
    """Return the static file name of a request, or None.

    Most files use the "static" endpoint. Some files have their own route
    under the static URL path (for example ``public.manifest``).
    """
    if req.endpoint == "static":
        return (req.view_args or {}).get("filename")
    prefix = (current_app.static_url_path or "/static").rstrip("/") + "/"
    if req.path.startswith(prefix):
        return req.path[len(prefix) :]
    return None


def compress_cache_key(req) -> str:
    """Return the Flask-Compress cache key: the path and the content hash."""
    filename = static_request_filename(req)
    return f"{req.path}:{static_file_hash(filename) if filename else ''}"


def compress_cache_backend() -> SimpleCache:
    """In-memory cache for compressed static files (one entry per encoding)."""
    return SimpleCache(threshold=500, default_timeout=0)


def init_static_assets(app: Flask) -> None:
    """Set up versioned static URLs, cache headers and compression."""
    if app.static_folder is None:
        return

    app.extensions[STATIC_HASHES_EXTENSION] = StaticFileHashes(app.static_folder)

    app.session_interface = StaticSkippingSessionInterface(  # type: ignore[assignment]
        app.session_interface, app.static_url_path or "/static"
    )

    from app.extensions import compress

    @app.url_defaults
    def add_static_version(endpoint, values):
        if endpoint != "static":
            return
        filename = values.get("filename")
        if not filename:
            return
        digest = static_file_hash(filename, app)
        if digest is not None:
            # Replace the "v=app_version" value that the templates send.
            values["v"] = digest

    @app.after_request
    def finish_static_response(response):
        filename = static_request_filename(request)
        if not filename:
            return response

        digest = static_file_hash(filename, app)

        if (
            digest is not None
            and request.args.get("v") == digest
            and response.status_code in (200, 304)
        ):
            response.cache_control.no_cache = None
            response.cache_control.public = True
            response.cache_control.max_age = IMMUTABLE_MAX_AGE
            response.cache_control.immutable = True
            response.expires = int(time.time() + IMMUTABLE_MAX_AGE)

        if (
            response.status_code == 200
            and response.mimetype in compress.compress_mimetypes_set
        ):
            # Read the file into memory, so that Flask-Compress can cache the
            # compressed body and can use gzip (it does not stream gzip).
            response.direct_passthrough = False
            response.make_sequence()
            response = compress.after_request(response)

        return response
