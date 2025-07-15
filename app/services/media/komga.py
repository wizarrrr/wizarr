import datetime
import logging
import re
from typing import Any

from sqlalchemy import or_

from app.extensions import db
from app.models import Invitation, Library, User
from app.services.invites import is_invite_valid, mark_server_used
from app.services.notifications import notify

from .client_base import RestApiMixin, register_media_client

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")


@register_media_client("komga")
class KomgaClient(RestApiMixin):
    """Wrapper around the Komga REST API using credentials from Settings."""

    def __init__(self, *args, **kwargs):
        if "url_key" not in kwargs:
            kwargs["url_key"] = "server_url"
        if "token_key" not in kwargs:
            kwargs["token_key"] = "api_key"
        super().__init__(*args, **kwargs)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def libraries(self) -> dict[str, str]:
        """Return mapping of library_id -> library_name."""
        try:
            response = self.get("/api/v1/libraries")
            libraries = response.json()
            return {lib["id"]: lib["name"] for lib in libraries}
        except Exception as e:
            logging.error(f"Failed to get Komga libraries: {e}")
            return {}

    def scan_libraries(
        self, url: str | None = None, token: str | None = None
    ) -> dict[str, str]:
        """Scan available libraries on this Komga server.

        Args:
            url: Optional server URL override
            token: Optional API token override

        Returns:
            dict: Library name -> library ID mapping
        """
        import requests

        if url and token:
            # Use override credentials for scanning
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{url.rstrip('/')}/api/v1/libraries", headers=headers, timeout=10
            )
            response.raise_for_status()
            libraries = response.json()
        else:
            # Use saved credentials
            response = self.get("/api/v1/libraries")
            libraries = response.json()

        return {lib["name"]: lib["id"] for lib in libraries}

    def create_user(self, username: str, password: str, email: str) -> str:
        """Create a new Komga user and return the user ID."""
        payload = {"email": email, "password": password, "roles": ["USER"]}
        response = self.post("/api/v1/users", json=payload)
        return response.json()["id"]

    def update_user(self, user_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a Komga user."""
        response = self.patch(f"/api/v1/users/{user_id}", json=updates)
        return response.json()

    def delete_user(self, user_id: str) -> None:
        """Delete a Komga user."""
        self.delete(f"/api/v1/users/{user_id}")

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get a Komga user by ID."""
        response = self.get(f"/api/v1/users/{user_id}")
        return response.json()

    def list_users(self) -> list[User]:
        """Sync users from Komga into the local DB and return the list of User records."""
        try:
            response = self.get("/api/v1/users")
            komga_users = {u["id"]: u for u in response.json()}

            for komga_user in komga_users.values():
                existing = User.query.filter_by(token=komga_user["id"]).first()
                if not existing:
                    new_user = User(
                        token=komga_user["id"],
                        username=komga_user["email"],
                        email=komga_user["email"],
                        code="empty",
                        server_id=getattr(self, "server_id", None),
                    )
                    db.session.add(new_user)
            db.session.commit()

            to_check = User.query.filter(
                User.server_id == getattr(self, "server_id", None)
            ).all()
            for db_user in to_check:
                if db_user.token not in komga_users:
                    db.session.delete(db_user)
            db.session.commit()

            return User.query.filter(
                User.server_id == getattr(self, "server_id", None)
            ).all()
        except Exception as e:
            logging.error(f"Failed to list Komga users: {e}")
            return []

    def _set_library_access(self, user_id: str, library_ids: list[str]) -> None:
        """Set library access for a user."""
        if not library_ids:
            return

        try:
            for library_id in library_ids:
                self.put(f"/api/v1/users/{user_id}/shared-libraries/{library_id}")
        except Exception as e:
            logging.warning(f"Failed to set library access for user {user_id}: {e}")

    def join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        """Handle public sign-up via invite for Komga servers."""
        if not EMAIL_RE.fullmatch(email):
            return False, "Invalid e-mail address."
        if not 8 <= len(password) <= 20:
            return False, "Password must be 8–20 characters."
        if password != confirm:
            return False, "Passwords do not match."

        ok, msg = is_invite_valid(code)
        if not ok:
            return False, msg

        existing = User.query.filter(
            or_(User.username == username, User.email == email),
            User.server_id == getattr(self, "server_id", None),
        ).first()
        if existing:
            return False, "User or e-mail already exists."

        try:
            user_id = self.create_user(username, password, email)

            inv = Invitation.query.filter_by(code=code).first()

            current_server_id = getattr(self, "server_id", None)
            if inv and inv.libraries:
                library_ids = [
                    lib.external_id
                    for lib in inv.libraries
                    if lib.server_id == current_server_id
                ]
            else:
                library_ids = [
                    lib.external_id
                    for lib in Library.query.filter_by(
                        enabled=True, server_id=current_server_id
                    ).all()
                ]

            self._set_library_access(user_id, library_ids)

            expires = None
            if inv and inv.duration:
                days = int(inv.duration)
                expires = datetime.datetime.utcnow() + datetime.timedelta(days=days)

            new_user = self._create_user_with_identity_linking(
                {
                    "username": username,
                    "email": email,
                    "token": user_id,
                    "code": code,
                    "expires": expires,
                    "server_id": current_server_id,
                }
            )
            db.session.commit()

            if inv:
                inv.used_by = new_user
                server_id = getattr(new_user, "server_id", None)
                if server_id is not None:
                    mark_server_used(inv, server_id)

            notify(
                "New User",
                f"User {username} has joined your server! 🎉",
                tags="tada",
            )

            return True, ""

        except Exception:
            logging.error("Komga join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred."

    def now_playing(self) -> list[dict[str, Any]]:
        """Return a list of currently playing sessions from Komga.

        Note: Komga is a comic/manga server and doesn't provide session
        tracking or "now playing" functionality like media streaming servers.
        This method always returns an empty list.

        Returns:
            list: Always returns an empty list since Komga doesn't track active sessions.
        """
        logging.debug(
            "Komga: No session tracking available - Komga doesn't provide now-playing functionality"
        )
        return []

    def statistics(self) -> dict[str, Any]:
        """Return essential Komga server statistics for the dashboard.

        Only collects data actually used by the UI:
        - Server version for health card
        - Active sessions count for health card (always 0 for Komga)
        - Transcoding sessions count for health card (always 0 for Komga)
        - Total users count for health card

        Returns:
            dict: Server statistics with minimal API calls
        """
        try:
            stats = {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
            }

            # User statistics - only what's displayed in UI
            try:
                users_response = self.get("/api/v1/users").json()
                stats["user_stats"] = {
                    "total_users": len(users_response),
                    "active_sessions": 0,  # Komga doesn't have active sessions concept
                }
            except Exception as e:
                logging.error(f"Failed to get Komga user stats: {e}")
                stats["user_stats"] = {"total_users": 0, "active_sessions": 0}

            # Server statistics - only version
            try:
                actuator_response = self.get("/api/v1/actuator/info").json()
                stats["server_stats"] = {
                    "version": actuator_response.get("build", {}).get(
                        "version", "Unknown"
                    ),
                    "transcoding_sessions": 0,  # Komga doesn't transcode
                }
            except Exception as e:
                logging.error(f"Failed to get Komga server stats: {e}")
                stats["server_stats"] = {}

            return stats

        except Exception as e:
            logging.error(f"Failed to get Komga statistics: {e}")
            return {
                "library_stats": {},
                "user_stats": {},
                "server_stats": {},
                "content_stats": {},
                "error": str(e),
            }
