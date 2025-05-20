from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
from cachetools import cached, TTLCache
from app.extensions import db
from app.models import Settings, User

class PlexClient:
    """Thin wrapper that knows how to connect with the *admin* credentials."""
    def __init__(self):
        # grab the raw .value from Settings
        self.token = (
            db.session
              .query(Settings.value)
              .filter_by(key="api_key")
              .scalar()
        )
        self.url = (
            db.session
              .query(Settings.value)
              .filter_by(key="server_url")
              .scalar()
        )
        self._server = None
        self._admin  = None

    @property
    def server(self) -> PlexServer:
        if self._server is None:
            self._server = PlexServer(self.url, self.token)
        return self._server

    @property
    def admin(self) -> MyPlexAccount:
        if self._admin is None:
            self._admin = MyPlexAccount(token=self.token)
        return self._admin

    def libraries(self):
        return [lib.title for lib in self.server.library.sections()]

    def invite_friend(self, email: str, sections: list[str], allow_sync: bool):
        self.admin.inviteFriend(
            user=email, server=self.server,
            sections=sections, allowSync=allow_sync,
        )

    def invite_home(self, email: str, sections: list[str], allow_sync: bool):
        self.admin.createExistingUser(
            user=email, server=self.server,
            sections=sections, allowSync=allow_sync,
        )

    def get_user(self, db_id: int) -> dict:
        # SQLAlchemy version of User.get_by_id(db_id)
        user_record = User.query.get(db_id)
        if not user_record:
            raise ValueError(f"No user found with id {db_id}")

        email = user_record.email
        plex_user = self.admin.user(email)
        return {
            "Name": plex_user.title,
            "Id":   plex_user.id,
            "Configuration": {
                "allowCameraUpload": plex_user.allowCameraUpload,
                "allowChannels":     plex_user.allowChannels,
                "allowSync":         plex_user.allowSync,
            },
            "Policy": {"sections": "na"},
        }

    def update_user(self, info: dict, form: dict) -> None:
        self.admin.updateFriend(
            info["Name"],
            self.server,
            allowSync=bool(form.get("allowSync")),
            allowChannels=bool(form.get("allowChannels")),
            allowCameraUpload=bool(form.get("allowCameraUpload")),
        )

    def remove_user(self, email: str):
        try:
            self.admin.removeHomeUser(email)
        except Exception:
            self.admin.removeFriend(email)


def scan_libraries(url: str, token: str) -> list[str]:
    return [lib.title for lib in PlexServer(url, token).library.sections()]
