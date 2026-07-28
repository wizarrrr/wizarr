from unittest.mock import patch

from app.extensions import db
from app.models import AdminAccount, Invitation, MediaServer, Settings


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class PolicyCapturingClient:
    def __init__(self):
        self.user_id = "emby-user-1"
        self.policy_updates = []

    def create_user(self, username, password):
        return self.user_id

    def get(self, endpoint):
        assert endpoint == f"/Users/{self.user_id}"
        return _Response(
            {
                "Policy": {
                    "IsAdministrator": True,
                    "EnableContentDeletion": True,
                    "EnableContentDownloading": True,
                    "EnableLiveTvAccess": True,
                    "EnableLiveTvManagement": True,
                    "AllowCameraUpload": True,
                    "EnablePublicSharing": True,
                    "AllowSharingPersonalItems": True,
                    "EnableSubtitleManagement": True,
                    "EnableRemoteControlOfOtherUsers": True,
                }
            }
        )

    def set_policy(self, user_id, policy):
        assert user_id == self.user_id
        self.policy_updates.append(policy)


def _complete_setup():
    admin = AdminAccount(username="admin")
    admin.set_password("password")
    db.session.add(admin)
    db.session.add(Settings(key="admin_username", value="admin"))


def test_password_prompt_applies_safe_emby_policy(client, session):
    _complete_setup()
    server = MediaServer(
        name="Emby",
        server_type="emby",
        url="http://emby.local",
        api_key="emby-key",
        allow_downloads=False,
        allow_live_tv=False,
        allow_mobile_uploads=False,
    )
    invitation = Invitation(
        code="EMBYPOLICY",
        used=False,
        unlimited=True,
        allow_downloads=False,
        allow_live_tv=False,
        allow_mobile_uploads=False,
    )
    invitation.servers = [server]
    db.session.add_all([server, invitation])
    db.session.commit()

    media_client = PolicyCapturingClient()

    with patch(
        "app.services.media.service.get_client_for_media_server",
        return_value=media_client,
    ):
        response = client.post(
            "/j/EMBYPOLICY/password",
            data={
                "username": "viewer",
                "email": "viewer@example.com",
                "password": "password123",
                "confirm": "password123",
            },
        )

    assert response.status_code == 302
    assert len(media_client.policy_updates) == 1
    policy = media_client.policy_updates[0]
    assert policy["IsAdministrator"] is False
    assert policy["EnableContentDeletion"] is False
    assert policy["EnableContentDownloading"] is False
    assert policy["EnableLiveTvAccess"] is False
    assert policy["EnableLiveTvManagement"] is False
    assert policy["AllowCameraUpload"] is False
    assert policy["EnablePublicSharing"] is False
    assert policy["AllowSharingPersonalItems"] is False
    assert policy["EnableSubtitleManagement"] is False
    assert policy["EnableRemoteControlOfOtherUsers"] is False
