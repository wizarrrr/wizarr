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

from abc import ABC, abstractmethod
from typing import Optional

from app.extensions import db
from app.models import Settings, MediaServer

# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

# Holds mapping of server_type -> MediaClient subclass
CLIENTS: dict[str, type["MediaClient"]] = {}


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

    # NOTE: keep *url_key* & *token_key* keyword arguments so older subclass
    # calls (e.g. super().__init__(url_key="server_url")) continue to work.

    def __init__(
        self,
        media_server: Optional[MediaServer] = None,
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
                db.session.query(MediaServer)
                .filter_by(server_type=server_type)
                .first()
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

        self.url = (
            db.session.query(Settings.value).filter_by(key=url_key).scalar()
        )
        self.token = (
            db.session.query(Settings.value).filter_by(key=token_key).scalar()
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _attach_server_row(self, row: MediaServer):
        """Populate instance attributes from a MediaServer row."""

        self.server_row: MediaServer = row
        self.server_id: int = row.id  # type: ignore[attr-defined]
        self.url: str = row.url  # type: ignore[attr-defined]
        self.token: str = row.api_key  # type: ignore[attr-defined]

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