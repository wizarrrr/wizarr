from __future__ import annotations

"""Romm media‐server client.

This minimal implementation lets Wizarr recognise RomM as a media‐server
backend so that an admin can store RomM connection credentials, scan the
list of *platforms* (treated as "libraries"), and present basic read‐only
user information in the UI.

NOTE – RomM exposes a comprehensive HTTP API that is documented via
OpenAPI (see /api/docs on any RomM instance).  To keep the initial
integration small we only implement the endpoints that Wizarr currently
needs:

    * GET /api/platforms  –>  list of platforms (= libraries)
    * GET /api/users      –>  list all users (admin only)

Future work can extend the client with create/update/delete operations
should Wizarr move towards full RomM user-management.
"""

import logging
from typing import Any, Dict, List

from app.extensions import db
from app.models import User
from .client_base import RestApiMixin, register_media_client

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


@register_media_client("romm")
class RommClient(RestApiMixin):
    """Very small wrapper around the RomM REST API."""

    API_PREFIX = "/api"

    def __init__(self, *args, **kwargs):
        # Defaults for historical callers
        kwargs.setdefault("url_key", "server_url")
        kwargs.setdefault("token_key", "api_key")
        super().__init__(*args, **kwargs)

    def _headers(self) -> Dict[str, str]:  # type: ignore[override]
        headers: Dict[str, str] = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # ------------------------------------------------------------------
    # Wizarr API – libraries
    # ------------------------------------------------------------------

    def libraries(self) -> Dict[str, str]:
        """Return mapping ``platform_id`` → ``display_name``.

        RomM's *platforms* endpoint returns JSON like::

            [ {"id": "nes", "name": "Nintendo Entertainment System", ...}, ... ]
        """
        try:
            r = self.get(f"{self.API_PREFIX}/platforms")
            data: List[Dict[str, Any]] = r.json()
            return {p["id"]: p.get("name", p["id"]) for p in data}
        except Exception as exc:  # noqa: BLE001
            logging.warning("ROMM: failed to fetch platforms – %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Wizarr API – users (read-only)
    # ------------------------------------------------------------------

    def list_users(self) -> List[User]:
        """Sync RomM users into local DB (read-only).

        Requires the supplied API token to belong to a RomM *admin* user as
        `/api/users` is admin-only.
        """
        try:
            r = self.get(f"{self.API_PREFIX}/users")
            remote_users: List[Dict[str, Any]] = r.json()
        except Exception as exc:  # noqa: BLE001
            logging.warning("ROMM: failed to list users – %s", exc)
            return []

        remote_by_id = {u["id"]: u for u in remote_users if "id" in u}

        # 1) upsert basic user rows so Wizarr UI has something to show
        for romm_id, ru in remote_by_id.items():
            db_row: User | None = (
                User.query.filter_by(token=romm_id, server_id=getattr(self, "server_id", None)).first()
            )
            if not db_row:
                db_row = User(
                    token=romm_id,
                    username=ru.get("username", "romm-user"),
                    email=ru.get("email", ""),
                    code="romm",  # placeholder – no invite code
                    password="romm",  # placeholder
                    server_id=getattr(self, "server_id", None),
                )
                db.session.add(db_row)
            else:
                db_row.username = ru.get("username", db_row.username)
                db_row.email = ru.get("email", db_row.email)
        db.session.commit()

        # 2) Remove local users that no longer exist upstream
        for local in (
            User.query.filter(User.server_id == getattr(self, "server_id", None)).all()
        ):
            if local.token not in remote_by_id:
                db.session.delete(local)
        db.session.commit()

        return (
            User.query.filter(User.server_id == getattr(self, "server_id", None)).all()
        )

    # ------------------------------------------------------------------
    # Un-implemented mutating operations
    # ------------------------------------------------------------------

    # Even though Wizarr currently doesn't expose UI to mutate RomM users, we
    # provide simple wrappers so future work (or API consumers) can call them.

    def create_user(self, username: str, password: str, email: str | None = None) -> str:
        """Create a RomM user and return the new ``user_id``.

        Only *username* and *password* are mandatory according to RomM docs.
        """
        payload: Dict[str, Any] = {
            "username": username,
            "password": password,
        }
        if email:
            payload["email"] = email

        r = self.post(f"{self.API_PREFIX}/users", json=payload)
        data = r.json() or {}
        return data.get("id") or data.get("user", {}).get("id")  # type: ignore[return-value]

    def update_user(self, user_id: str, patch: Dict[str, Any]):
        """PATCH selected fields on a RomM user object."""
        return self.patch(f"{self.API_PREFIX}/users/{user_id}", json=patch).json()

    def delete_user(self, user_id: str):
        resp = self.delete(f"{self.API_PREFIX}/users/{user_id}")
        if resp.status_code not in (200, 204):
            resp.raise_for_status()

    def get_user(self, user_id: str) -> Dict[str, Any]:
        r = self.get(f"{self.API_PREFIX}/users/{user_id}")
        return r.json() 