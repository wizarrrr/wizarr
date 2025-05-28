import logging
import requests

from app.extensions import db
from app.models import User
from .client_base import MediaClient, register_media_client


@register_media_client("emby")
class EmbyClient(MediaClient):
    """Wrapper around the Emby REST API using credentials from Settings."""

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
            timeout=10,
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
        # Emby: create user (without password), then set password in a separate call.
        user = self.post("/Users/New", {"Name": username}).json()
        user_id = user["Id"]
        # Update the user's password
        self.post(
            f"/Users/{user_id}/Password",
            {"Id": user_id, "NewPw": password, "ResetPassword": True},
        )
        return user_id

    def set_policy(self, user_id: str, policy: dict) -> None:
        self.post(f"/Users/{user_id}/Policy", policy)

    def delete_user(self, user_id: str) -> None:
        self.delete(f"/Users/{user_id}")

    def get_user(self, emby_id: str) -> dict:
        return self.get(f"/Users/{emby_id}").json()

    def update_user(self, emby_id: str, form: dict) -> dict | None:
        current = self.get_user(emby_id)

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

        return self.post(f"/Users/{emby_id}", current).json()

    def list_users(self) -> list[User]:
        """Sync users from Emby into the local DB and return the list of User records."""
        emby_users = {u["Id"]: u for u in self.get("/Users").json()}

        for emby in emby_users.values():
            existing = User.query.filter_by(token=emby["Id"]).first()
            if not existing:
                new = User(
                    token=emby["Id"],
                    username=emby["Name"],
                    email="empty",
                    code="empty",
                    password="empty",
                ) 
                db.session.add(new)
        db.session.commit()

        for dbu in User.query.all():
            if dbu.token not in emby_users:
                db.session.delete(dbu)
        db.session.commit()

        return User.query.all()