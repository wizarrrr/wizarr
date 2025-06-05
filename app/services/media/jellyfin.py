import datetime
import logging
import re
from sqlalchemy import or_

import requests

from app.extensions import db
from app.models import Invitation, User, Settings, Library
from app.services.notifications import notify
from app.services.invites import is_invite_valid
from .client_base import MediaClient, register_media_client

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}$")


@register_media_client("jellyfin")
class JellyfinClient(MediaClient):
    """Wrapper around the Jellyfin REST API using credentials from Settings."""

    def __init__(self):
        super().__init__(url_key="server_url", token_key="api_key")

    @property
    def hdrs(self):
        return {"X-Emby-Token": self.token}

    def get(self, path: str):
        r = requests.get(f"{self.url}{path}", headers=self.hdrs, timeout=10)
        logging.info("GET  %s%s → %s", self.url, path, r.status_code)
        r.raise_for_status()
        return r

    def post(self, path: str, payload: dict):
        r = requests.post(
            f"{self.url}{path}",
            json=payload,
            headers=self.hdrs,
            timeout=10
        )
        logging.info("POST %s%s → %s", self.url, path, r.status_code)
        r.raise_for_status()
        return r

    def delete(self, path: str):
        r = requests.delete(f"{self.url}{path}", headers=self.hdrs, timeout=10)
        logging.info("DEL  %s%s → %s", self.url, path, r.status_code)
        r.raise_for_status()
        return r

    def libraries(self) -> dict[str, str]:
        return {
            item["Id"]: item["Name"]
            for item in self.get("/Library/MediaFolders").json()["Items"]
        }

    def create_user(self, username: str, password: str) -> str:
        return self.post(
            "/Users/New",
            {"Name": username, "Password": password}
        ).json()["Id"]

    def set_policy(self, user_id: str, policy: dict) -> None:
        self.post(f"/Users/{user_id}/Policy", policy)

    def delete_user(self, user_id: str) -> None:
        self.delete(f"/Users/{user_id}")

    def get_user(self, jf_id: str) -> dict:
        return self.get(f"/Users/{jf_id}").json()

    def update_user(self, jf_id: str, form: dict) -> dict | None:
        current = self.get_user(jf_id)

        for key, val in form.items():
            for section in ("Policy", "Configuration"):
                if key in current[section]:
                    target = current[section][key]
                    if isinstance(target, bool):
                        val = (val == "True")
                    elif isinstance(target, int):
                        val = int(val)
                    elif isinstance(target, list):
                        val = [] if val == "" else val.split(", ")
                    current[section][key] = val

        return self.post(f"/Users/{jf_id}", current).json()

    def list_users(self) -> list[User]:
        """Sync users from Jellyfin into the local DB and return the list of User records."""
        jf_users = {u["Id"]: u for u in self.get("/Users").json()}

        for jf in jf_users.values():
            existing = User.query.filter_by(token=jf["Id"]).first()
            if not existing:
                new = User(
                    token=jf["Id"],
                    username=jf["Name"],
                    email="empty",
                    code="empty",
                    password="empty"
                )
                db.session.add(new)
        db.session.commit()

        for dbu in User.query.all():
            if dbu.token not in jf_users:
                db.session.delete(dbu)
        db.session.commit()

        return User.query.all()

    # --- helpers -----------------------------------------------------

    def _password_for_db(self, password: str) -> str:
        """Return the password value to store in the local DB."""
        return password

    @staticmethod
    def _mark_invite_used(inv: Invitation, user: User) -> None:
        inv.used = True if not inv.unlimited else inv.used
        inv.used_at = datetime.datetime.now()
        inv.used_by = user
        db.session.commit()

    @staticmethod
    def _folder_name_to_id(name: str, cache: dict[str, str]) -> str | None:
        """Resolve a folder name or ID to the server ID."""

        # Allow passing the actual ID directly
        if name in cache.values():
            return name

        return cache.get(name)

    def _set_specific_folders(self, user_id: str, names: list[str]):
        mapping = {
            item["Name"]: item["Id"]
            for item in self.get("/Library/MediaFolders").json()["Items"]
        }

        # Also map IDs directly for convenience
        mapping.update({v: v for v in mapping.values()})

        folder_ids = [self._folder_name_to_id(n, mapping) for n in names]
        folder_ids = [fid for fid in folder_ids if fid]

        policy_patch = {
            "EnableAllFolders": not folder_ids,
            "EnabledFolders": folder_ids,
        }

        current = self.get(f"/Users/{user_id}").json()["Policy"]
        current.update(policy_patch)
        self.set_policy(user_id, current)

    # --- public sign-up ---------------------------------------------

    def join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
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
            or_(User.username == username, User.email == email)
        ).first()
        if existing:
            return False, "User or e-mail already exists."

        try:
            user_id = self.create_user(username, password)

            inv = Invitation.query.filter_by(code=code).first()

            if inv.libraries:
                sections = [lib.external_id for lib in inv.libraries]
            else:
                sections = [
                    lib.external_id
                    for lib in Library.query.filter_by(enabled=True).all()
                ]

            self._set_specific_folders(user_id, sections)

            expires = None
            if inv.duration:
                days = int(inv.duration)
                expires = datetime.datetime.utcnow() + datetime.timedelta(days=days)

            new_user = User(
                username=username,
                email=email,
                password=self._password_for_db(password),
                token=user_id,
                code=code,
                expires=expires,
            )
            db.session.add(new_user)
            db.session.commit()

            self._mark_invite_used(inv, new_user)
            notify(
                "New User",
                f"User {username} has joined your server! 🎉",
                tags="tada",
            )

            return True, ""

        except Exception:  # noqa: BLE001
            logging.error("Jellyfin join error", exc_info=True)
            db.session.rollback()
            return False, "An unexpected error occurred."

# ─── Admin-side helpers – mirror the Plex API we already exposed ──────────
