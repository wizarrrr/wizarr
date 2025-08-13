"""Test invitation server defaulting behavior."""

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


class TestInvitationServerDefaulting:
    """Test server defaulting behavior for invitation creation."""

    def test_single_server_requires_specification(self, app, client, api_key):
        """Test that even with only one server, server_ids must be specified."""
        with app.app_context():
            # Create one verified server
            server = MediaServer(
                name="Only Server",
                server_type="plex",
                url="http://localhost:32400",
                api_key="test_key",
                verified=True,
            )
            db.session.add(server)
            db.session.commit()

            # Create invitation without specifying server_ids (should fail)
            data = {"duration": "30", "unlimited": False}

            response = client.post(
                "/api/invitations",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                data=json.dumps(data),
            )

            assert response.status_code == 400
            response_data = response.get_json()
            assert "error" in response_data
            assert "Server selection is required" in response_data["error"]
            assert "available_servers" in response_data
            assert len(response_data["available_servers"]) == 1
            assert response_data["available_servers"][0]["name"] == "Only Server"

            # Now create invitation with explicit server_ids (should work)
            data["server_ids"] = [server.id]
            response = client.post(
                "/api/invitations",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                data=json.dumps(data),
            )

            assert response.status_code == 201
            response_data = response.get_json()
            assert "invitation" in response_data
            invitation = Invitation.query.first()
            assert invitation is not None
            assert len(invitation.servers) == 1
            assert invitation.servers[0].id == server.id

    def test_multiple_servers_require_specification(self, app, client, api_key):
        """Test that with multiple servers, explicit specification is required."""
        with app.app_context():
            # Create two verified servers
            server1 = MediaServer(
                name="Server 1",
                server_type="plex",
                url="http://localhost:32400",
                api_key="test_key1",
                verified=True,
            )
            server2 = MediaServer(
                name="Server 2",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key2",
                verified=True,
            )
            db.session.add_all([server1, server2])
            db.session.commit()

            # Try to create invitation without specifying server_ids
            data = {"duration": "30", "unlimited": False}

            response = client.post(
                "/api/invitations",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                data=json.dumps(data),
            )

            assert response.status_code == 400
            response_data = response.get_json()
            assert "Server selection is required" in response_data["error"]
            assert "available_servers" in response_data
            assert len(response_data["available_servers"]) == 2

    def test_explicit_server_selection(self, app, client, api_key):
        """Test explicit server selection works correctly."""
        with app.app_context():
            # Create two verified servers
            server1 = MediaServer(
                name="Server 1",
                server_type="plex",
                url="http://localhost:32400",
                api_key="test_key1",
                verified=True,
            )
            server2 = MediaServer(
                name="Server 2",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key2",
                verified=True,
            )
            db.session.add_all([server1, server2])
            db.session.commit()

            # Create invitation specifying server_ids
            data = {
                "duration": "30",
                "unlimited": False,
                "server_ids": [server2.id],  # Choose server 2
            }

            response = client.post(
                "/api/invitations",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                data=json.dumps(data),
            )

            assert response.status_code == 201
            response_data = response.get_json()
            assert "invitation" in response_data

            # Verify invitation was created with the specified server
            invitation = Invitation.query.first()
            assert invitation is not None
            assert len(invitation.servers) == 1
            assert invitation.servers[0].id == server2.id

    def test_invalid_server_ids(self, app, client, api_key):
        """Test that invalid server IDs are rejected."""
        with app.app_context():
            # Create one verified server
            server = MediaServer(
                name="Valid Server",
                server_type="plex",
                url="http://localhost:32400",
                api_key="test_key",
                verified=True,
            )
            db.session.add(server)
            db.session.commit()

            # Try to create invitation with invalid server ID
            data = {
                "duration": "30",
                "unlimited": False,
                "server_ids": [99999],  # Non-existent server
            }

            response = client.post(
                "/api/invitations",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                data=json.dumps(data),
            )

            assert response.status_code == 400
            response_data = response.get_json()
            assert "not found or not verified" in response_data["error"]

    def test_unverified_server_rejected(self, app, client, api_key):
        """Test that unverified servers are not usable."""
        with app.app_context():
            # Create unverified server
            server = MediaServer(
                name="Unverified Server",
                server_type="plex",
                url="http://localhost:32400",
                api_key="test_key",
                verified=False,  # Not verified
            )
            db.session.add(server)
            db.session.commit()

            # Try to create invitation (should fail due to no verified servers)
            data = {"duration": "30", "unlimited": False}

            response = client.post(
                "/api/invitations",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                data=json.dumps(data),
            )

            assert response.status_code == 400
            response_data = response.get_json()
            assert "Server selection is required" in response_data["error"]
            # When no verified servers are available, the available_servers list should be empty
            assert "available_servers" in response_data
            assert len(response_data["available_servers"]) == 0

    def test_mixed_verified_unverified_servers(self, app, client, api_key):
        """Test behavior with mix of verified and unverified servers."""
        with app.app_context():
            # Create one verified and one unverified server
            verified_server = MediaServer(
                name="Verified Server",
                server_type="plex",
                url="http://localhost:32400",
                api_key="test_key1",
                verified=True,
            )
            unverified_server = MediaServer(
                name="Unverified Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key2",
                verified=False,
            )
            db.session.add_all([verified_server, unverified_server])
            db.session.commit()

            # Should require explicit server specification even with only one verified server
            data = {"duration": "30", "unlimited": False}

            response = client.post(
                "/api/invitations",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                data=json.dumps(data),
            )

            assert response.status_code == 400
            response_data = response.get_json()
            assert "Server selection is required" in response_data["error"]
            assert "available_servers" in response_data
            # Only the verified server should be in available_servers
            assert len(response_data["available_servers"]) == 1
            assert response_data["available_servers"][0]["name"] == "Verified Server"

            # Now create invitation with explicit server specification
            data["server_ids"] = [verified_server.id]
            response = client.post(
                "/api/invitations",
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                data=json.dumps(data),
            )

            assert response.status_code == 201
            response_data = response.get_json()
            assert "invitation" in response_data

            # Verify invitation uses only the verified server
            invitation = Invitation.query.first()
            assert invitation is not None
            assert len(invitation.servers) == 1
            assert invitation.servers[0].id == verified_server.id
