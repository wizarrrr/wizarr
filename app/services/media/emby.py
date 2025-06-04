import logging
import re
import datetime

from app.extensions import db
from app.models import User
from .jellyfin import JellyfinClient
from .client_base import register_media_client

# Reuse the same email regex as jellyfin
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")


@register_media_client("emby")
class EmbyClient(JellyfinClient):
    """Wrapper around the Emby REST API using credentials from Settings."""

    def libraries(self) -> dict[str, str]:
        return {
            item["Id"]: item["Name"]
            for item in self.get("/Library/MediaFolders").json()["Items"]
        }

    def create_user(self, username: str, password: str) -> str:
        """Create user and set password"""
        # Step 1: Create user without password
        user = self.post("/Users/New", {"Name": username}).json()
        user_id = user["Id"]
        
        # Step 2: Set password
        try:
            logging.info(f"Setting password for user {username} (ID: {user_id})")
            password_response = self.post(
                f"/Users/{user_id}/Password",
                {
                    "NewPw": password,
                    "CurrentPw": "",  # No current password for new users
                    "ResetPassword": False  # Important! Don't reset password
                }
            )
            logging.info(f"Password set response: {password_response.status_code}")
        except Exception as e:
            logging.error(f"Failed to set password for user {username}: {str(e)}")
            # Continue with user creation even if password setting fails
            # as we may need to debug further
        
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

    def _password_for_db(self, password: str) -> str:
        """Return placeholder password for local DB."""
        return "emby-user"

    def _set_specific_folders(self, user_id: str, names: list[str]):
        """Set library access for a user and ensure playback permissions."""
        super()._set_specific_folders(user_id, names)

        playback_permissions = {
            "EnableMediaPlayback": True,
            "EnableAudioPlaybackTranscoding": True,
            "EnableVideoPlaybackTranscoding": True,
            "EnablePlaybackRemuxing": True,
            "EnableContentDownloading": True,
            "EnableRemoteAccess": True,
        }

        current = self.get(f"/Users/{user_id}").json()["Policy"]
        current.update(playback_permissions)
        self.set_policy(user_id, current)
