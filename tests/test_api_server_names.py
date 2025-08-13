"""Test API invitation endpoints with server name enhancements."""

import hashlib
import json

import pytest

from app import create_app
from app.config import BaseConfig
from app.extensions import db
from app.models import AdminAccount, ApiKey, Invitation, MediaServer


class TestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def app():
    """Create application for testing."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()

        # Create a test admin account
        admin = AdminAccount(username="testadmin")
        admin.set_password("testpass")
        db.session.add(admin)
        db.session.commit()

    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def api_key(app):
    """Create a test API key."""
    with app.app_context():
        admin = AdminAccount.query.first()
        raw_key = "test_api_key_12345"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = ApiKey(
            name="Test API Key",
            key_hash=key_hash,
            created_by_id=admin.id,
            is_active=True,
        )
        db.session.add(api_key)
        db.session.commit()

        return raw_key


class TestInvitationAPIEnhancements:
    """Test API enhancements for invitation server names."""

    def test_list_invitations_with_server_info(self, app, client, api_key):
        """Test that listing invitations includes server information."""
        with app.app_context():
            # Create servers
            server1 = MediaServer(
                name="Plex Server",
                server_type="plex",
                url="http://localhost:32400",
                api_key="test_key1",
                verified=True,
            )
            server2 = MediaServer(
                name="Jellyfin Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key2",
                verified=True,
            )
            db.session.add_all([server1, server2])
            db.session.flush()

            # Create invitation with multiple servers
            invitation = Invitation(
                code="MULTISERVER", used=False, unlimited=False, duration="30"
            )
            db.session.add(invitation)
            db.session.flush()

            invitation.servers.extend([server1, server2])
            db.session.commit()

        # Test API call
        response = client.get("/api/invitations", headers={"X-API-Key": api_key})

        assert response.status_code == 200
        data = response.get_json()

        assert "invitations" in data
        assert len(data["invitations"]) == 1

        invite_data = data["invitations"][0]
        assert invite_data["code"] == "MULTISERVER"
        assert invite_data["display_name"] == "Plex Server, Jellyfin Server"
        assert invite_data["server_names"] == ["Plex Server", "Jellyfin Server"]
        assert invite_data["uses_global_setting"] is False

    def test_create_invitation_with_server_info(self, app, client, api_key):
        """Test that creating invitations returns server information."""
        with app.app_context():
            # Create a server
            server = MediaServer(
                name="My Test Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key",
                verified=True,
            )
            db.session.add(server)
            db.session.commit()

            # Create invitation
            data = {"duration": "30", "unlimited": False, "server_ids": [server.id]}

            response = client.post(
                "/api/invitations",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                data=json.dumps(data),
            )

            assert response.status_code == 201
            response_data = response.get_json()

            assert "invitation" in response_data
            invite_data = response_data["invitation"]

            assert invite_data["display_name"] == "My Test Server"
            assert invite_data["server_names"] == ["My Test Server"]
            assert invite_data["uses_global_setting"] is False

    def test_invitation_with_global_setting(self, app, client, api_key):
        """Test invitation API with global Display Name setting."""
        with app.app_context():
            from app.models import Settings

            # Create global setting
            setting = Settings(key="server_name", value="My Custom Media Center")

            # Create a server
            server = MediaServer(
                name="Actual Server Name",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key",
                verified=True,
            )
            db.session.add_all([setting, server])
            db.session.flush()

            # Create invitation
            invitation = Invitation(
                code="GLOBALSETTING", used=False, unlimited=False, duration="unlimited"
            )
            db.session.add(invitation)
            db.session.flush()

            invitation.servers.append(server)
            db.session.commit()

        # Test API call
        response = client.get("/api/invitations", headers={"X-API-Key": api_key})

        assert response.status_code == 200
        data = response.get_json()

        invite_data = data["invitations"][0]
        assert invite_data["display_name"] == "My Custom Media Center"
        assert invite_data["server_names"] == ["Actual Server Name"]
        assert invite_data["uses_global_setting"] is True

    def test_empty_server_list_fallback(self, app, client, api_key):
        """Test invitation with no associated servers."""
        with app.app_context():
            # Create invitation without servers
            invitation = Invitation(
                code="NOSERVERS", used=False, unlimited=False, duration="unlimited"
            )
            db.session.add(invitation)
            db.session.commit()

        # Test API call
        response = client.get("/api/invitations", headers={"X-API-Key": api_key})

        assert response.status_code == 200
        data = response.get_json()

        invite_data = data["invitations"][0]
        assert invite_data["display_name"] == "Unknown Server"
        assert invite_data["server_names"] == []
        assert invite_data["uses_global_setting"] is False
