#
# Media client abstraction & registry
# ----------------------------------
# Historically Wizarr stored the admin media-server credentials (URL & API key)
# in the generic Settings table.  We migrated these credentials to the new
# `MediaServer` table so Wizarr can manage several servers at once.  The base
# MediaClient now prefers to read credentials from a `MediaServer` row and only
# falls back to legacy Settings keys when no matching MediaServer exists (e.g.
# fresh installs that haven't yet completed the migration).

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import requests

from app.extensions import db
from app.models import MediaServer, Settings, User

# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

# Holds mapping of server_type -> MediaClient subclass
CLIENTS: dict[str, type[MediaClient]] = {}


def register_media_client(name: str):
    """Decorator to register a MediaClient under a given *server_type* name.

    We additionally annotate the class with the attribute ``_server_type`` so
    instances can later resolve the corresponding ``MediaServer`` row without
    external knowledge.
    """

    def decorator(cls):
        cls._server_type = name  # type: ignore[attr-defined]
        CLIENTS[name] = cls
        return cls

    return decorator


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class MediaClient(ABC):
    """Common helper wrapper around third-party media-server SDKs.

    On initialisation we attempt the following resolution order for
    ``url`` and ``token``:

    1. *Explicit* ``media_server`` row, if provided.
    2. First ``MediaServer`` record with a ``server_type`` matching the class.
    3. Legacy ``Settings`` keys (``server_url`` / ``api_key``) for backwards
       compatibility – these will be removed in a future release.
    """

    url: str | None
    token: str | None

    # NOTE: keep *url_key* & *token_key* keyword arguments so older subclass
    # calls (e.g. super().__init__(url_key="server_url")) continue to work.

    def __init__(
        self,
        media_server: MediaServer | None = None,
        *,
        url_key: str = "server_url",
        token_key: str = "api_key",
    ) -> None:
        # ------------------------------------------------------------------
        # 1. Direct MediaServer row supplied
        # ------------------------------------------------------------------
        if media_server is not None:
            self._attach_server_row(media_server)
            return

        # ------------------------------------------------------------------
        # 2. Lookup matching MediaServer by server_type (if available)
        # ------------------------------------------------------------------
        server_type = getattr(self.__class__, "_server_type", None)
        if server_type:
            row = (
                db.session.query(MediaServer).filter_by(server_type=server_type).first()
            )
            if row is not None:
                self._attach_server_row(row)
                return

        # ------------------------------------------------------------------
        # 3. Legacy Settings fallback
        # ------------------------------------------------------------------
        # When falling back we *do not* set ``server_row`` nor ``server_id`` –
        # callers relying on those attributes should migrate to supply a
        # MediaServer.

        self.url = db.session.query(Settings.value).filter_by(key=url_key).scalar()
        self.token = db.session.query(Settings.value).filter_by(key=token_key).scalar()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _attach_server_row(self, row: MediaServer):
        """Populate instance attributes from a MediaServer row."""

        self.server_row: MediaServer = row
        self.server_id: int = row.id  # type: ignore[attr-defined]
        self.url = row.url  # type: ignore[attr-defined]
        self.token = row.api_key  # type: ignore[attr-defined]

    def _create_user_with_identity_linking(self, user_kwargs: dict) -> User:
        """Create a User record with automatic identity linking for multi-server invitations.

        This helper ensures that users created from the same invitation code are
        automatically linked to a shared Identity, even when they don't have valid
        email addresses that would trigger the normal email-based linking.

        Args:
            user_kwargs: Dictionary of User model attributes

        Returns:
            User: The created User record with identity_id set if applicable
        """
        code = user_kwargs.get("code")

        # Check if this is part of a multi-server invitation
        if code:
            existing_user = User.query.filter_by(code=code).first()
            if existing_user and existing_user.identity_id:
                # Link to existing identity from same invitation
                user_kwargs["identity_id"] = existing_user.identity_id

        new_user = User(**user_kwargs)
        db.session.add(new_user)
        return new_user

    @abstractmethod
    def libraries(self):
        raise NotImplementedError

    @abstractmethod
    def create_user(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def update_user(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_user(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def list_users(self, *args, **kwargs):
        """Return a list of users for this media server. Subclasses must implement."""
        raise NotImplementedError

    @abstractmethod
    def now_playing(self):
        """Return a list of currently playing sessions for this media server.

        Returns:
            list: A list of session dictionaries with standardized keys including:
                - user_name: Name of the user currently playing
                - media_title: Title of the media being played
                - media_type: Type of media (movie, episode, track, etc.)
                - progress: Playback progress (0.0 to 1.0)
                - state: Playback state (playing, paused, buffering, stopped)
                - session_id: Unique identifier for the session
        """
        raise NotImplementedError

    @abstractmethod
    def statistics(self):
        """Return server statistics including library counts, user activity, etc.

        Returns:
            dict: A dictionary containing:
                - library_stats: Library breakdown with counts per type
                - user_stats: User activity and count information
                - server_stats: Server health and performance metrics
                - content_stats: Content consumption and popular items
        """
        raise NotImplementedError

    @abstractmethod
    def join(self, username: str, password: str, confirm: str, email: str, code: str):
        """Process user invitation for this media server.

        Args:
            username: Username for the new account
            password: Password for the new account
            confirm: Password confirmation
            email: Email address for the new account
            code: Invitation code being used

        Returns:
            tuple: (success: bool, message: str)
        """
        raise NotImplementedError

    @abstractmethod
    def scan_libraries(self, url: str | None = None, token: str | None = None):
        """Scan available libraries on this media server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Library name -> library ID mapping
        """
        raise NotImplementedError

    def invite_home(
        self, email: str, sections: list[str], allow_sync: bool, allow_channels: bool
    ):
        """Invite a user to the home server (if supported).

        Args:
            email: Email address of the user to invite
            sections: List of library sections to grant access to
            allow_sync: Whether to allow syncing
            allow_channels: Whether to allow channel access
        """
        raise NotImplementedError("invite_home not implemented for this server type")

    def invite_friend(
        self, email: str, sections: list[str], allow_sync: bool, allow_channels: bool
    ):
        """Invite a user as a friend (if supported).

        Args:
            email: Email address of the user to invite
            sections: List of library sections to grant access to
            allow_sync: Whether to allow syncing
            allow_channels: Whether to allow channel access
        """
        raise NotImplementedError("invite_friend not implemented for this server type")


# ---------------------------------------------------------------------------
# Shared helpers for simple REST JSON backends
# ---------------------------------------------------------------------------


class RestApiMixin(MediaClient):
    """Mixin that adds minimal HTTP helpers for JSON-based REST APIs.

    Subclasses only need to implement ``_headers`` if they require
    authentication headers beyond the defaults.  The mixin centralises
    logging, error handling and URL joining so individual back-ends can keep
    their method bodies small and readable.
    """

    # ------------------------------------------------------------------
    # Customisation hooks
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:  # noqa: D401
        """Return default headers for every request (override as needed)."""
        return {
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Thin wrappers around ``requests`` so subclasses never import it
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs):
        if self.url is None:
            raise ValueError("Media server URL is not set.")
        url = f"{self.url.rstrip('/')}" + path
        hdrs = {**self._headers(), **kwargs.pop("headers", {})}

        logging.info("%s %s", method.upper(), url)
        resp = requests.request(method, url, headers=hdrs, timeout=10, **kwargs)
        logging.info("→ %s", resp.status_code)
        resp.raise_for_status()
        return resp

    # Convenience helpers ------------------------------------------------

    def get(self, path: str, **kwargs):
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self._request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs):
        return self._request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self._request("DELETE", path, **kwargs)

    def put(self, path: str, **kwargs):
        return self._request("PUT", path, **kwargs)
