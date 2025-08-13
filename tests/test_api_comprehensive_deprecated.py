"""Comprehensive API endpoint tests for Wizarr."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from app import create_app
from app.config import BaseConfig
from app.extensions import db
from app.models import AdminAccount, ApiKey, Invitation, Library, MediaServer, User


class TestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture(scope="session")
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

        # Check if API key already exists
        existing_key = ApiKey.query.filter_by(key_hash=key_hash).first()
        if existing_key:
            return raw_key

        api_key = ApiKey(
            name="Test API Key",
            key_hash=key_hash,
            created_by_id=admin.id,
            is_active=True,
        )
        db.session.add(api_key)
        db.session.commit()

        return raw_key


@pytest.fixture
def sample_data(app):
    """Create sample data for testing."""
    with app.app_context():
        # Clean up any existing data first
        MediaServer.query.delete()
        Library.query.delete()
        User.query.delete()
        Invitation.query.delete()
        db.session.commit()

        # Create media server
        server = MediaServer(
            name="Test Plex Server",
            server_type="plex",
            url="http://localhost:32400",
            api_key="test_plex_key",
            verified=True,
        )
        db.session.add(server)
        db.session.flush()

        # Create library
        library = Library(external_id="1", name="Movies", server_id=server.id)
        db.session.add(library)
        db.session.flush()

        # Create user
        user = User(
            token="test_user_token",
            username="testuser",
            email="test@example.com",
            code="ABC123",
            expires=datetime.now(UTC) + timedelta(days=30),
            server_id=server.id,
        )
        db.session.add(user)
        db.session.flush()

        # Create invitation
        invitation = Invitation(
            code="INV123",
            expires=datetime.now(UTC) + timedelta(days=7),
            duration="30",
            unlimited=False,
            server_id=server.id,
        )
        db.session.add(invitation)

        db.session.commit()

        # Return IDs instead of objects to avoid session issues
        return {
            "server_id": server.id,
            "library_id": library.id,
            "user_id": user.id,
            "invitation_id": invitation.id,
        }


class TestAPIStatus:
    """Test the API status endpoint."""

    def test_status_without_key(self, client):
        """Test status endpoint without API key."""
        response = client.get("/api/status")
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "Unauthorized"

    def test_status_with_invalid_key(self, client):
        """Test status endpoint with invalid API key."""
        response = client.get("/api/status", headers={"X-API-Key": "invalid_key"})
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "Unauthorized"

    def test_status_with_valid_key(self, client, api_key, sample_data):
        """Test status endpoint with valid API key."""
        response = client.get("/api/status", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        data = response.get_json()
        assert "users" in data
        assert "invites" in data
        assert "pending" in data
        assert "expired" in data
        assert data["users"] == 1
        assert data["invites"] == 1
        assert data["pending"] == 1
        assert data["expired"] == 0


class TestAPIUsers:
    """Test the API users endpoints."""

    def test_list_users_unauthorized(self, client):
        """Test users list without authentication."""
        response = client.get("/api/users")
        assert response.status_code == 401

    def test_list_users_success(self, client, api_key, sample_data):
        """Test successful users list."""
        response = client.get("/api/users", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        data = response.get_json()
        assert "users" in data
        assert "count" in data
        assert data["count"] == len(data["users"])

        # Check user data structure
        if data["users"]:
            user = data["users"][0]
            assert "id" in user
            assert "username" in user
            assert "email" in user
            assert "server" in user
            assert "server_type" in user

    def test_delete_user_unauthorized(self, client, sample_data):
        """Test user deletion without authentication."""
        response = client.delete(f"/api/users/{sample_data['user_id']}")
        assert response.status_code == 401

    def test_delete_user_not_found(self, client, api_key):
        """Test deletion of non-existent user."""
        response = client.delete("/api/users/99999", headers={"X-API-Key": api_key})
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_extend_user_expiry_unauthorized(self, client, sample_data):
        """Test user expiry extension without authentication."""
        response = client.post(
            f"/api/users/{sample_data['user_id']}/extend",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"days": 30}),
        )
        assert response.status_code == 401

    def test_extend_user_expiry_success(self, client, api_key, sample_data):
        """Test successful user expiry extension."""
        user_id = sample_data["user_id"]
        data = {"days": 14}

        response = client.post(
            f"/api/users/{user_id}/extend",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            data=json.dumps(data),
        )
        assert response.status_code == 200

        response_data = response.get_json()
        assert "message" in response_data
        assert "new_expiry" in response_data
        assert "14 days" in response_data["message"]

    def test_extend_user_expiry_not_found(self, client, api_key):
        """Test expiry extension for non-existent user."""
        response = client.post(
            "/api/users/99999/extend",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            data=json.dumps({"days": 14}),
        )
        assert response.status_code == 404


class TestAPIInvitations:
    """Test the API invitations endpoints."""

    def test_list_invitations_unauthorized(self, client):
        """Test invitations list without authentication."""
        response = client.get("/api/invitations")
        assert response.status_code == 401

    def test_list_invitations_success(self, client, api_key, sample_data):
        """Test successful invitations list."""
        response = client.get("/api/invitations", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        data = response.get_json()
        assert "invitations" in data
        assert "count" in data
        assert data["count"] == len(data["invitations"])

        # Check invitation data structure
        if data["invitations"]:
            invitation = data["invitations"][0]
            assert "id" in invitation
            assert "code" in invitation
            assert "status" in invitation
            assert "created" in invitation
            assert "expires" in invitation
            assert "duration" in invitation
            # Test that URL is included in list response
            assert "url" in invitation
            assert invitation["url"].startswith("/j/")
            assert invitation["code"] in invitation["url"]

    def test_create_invitation_unauthorized(self, client):
        """Test invitation creation without authentication."""
        response = client.post(
            "/api/invitations",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"server_ids": [1]}),
        )
        assert response.status_code == 401

    def test_create_invitation_success(self, client, api_key, sample_data):
        """Test successful invitation creation."""
        data = {
            "server_ids": [sample_data["server_id"]],
            "expires_in_days": 7,
            "duration": "30",
            "unlimited": False,
            "library_ids": [sample_data["library_id"]],
        }

        response = client.post(
            "/api/invitations",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            data=json.dumps(data),
        )
        assert response.status_code == 201

        response_data = response.get_json()
        assert "message" in response_data
        assert "invitation" in response_data
        assert response_data["invitation"]["duration"] == "30"
        assert not response_data["invitation"]["unlimited"]
        # Test that URL is included
        assert "url" in response_data["invitation"]
        assert response_data["invitation"]["url"].startswith("/j/")
        assert response_data["invitation"]["code"] in response_data["invitation"]["url"]

    def test_create_invitation_default_values(self, client, api_key, sample_data):
        """Test invitation creation with default values."""
        response = client.post(
            "/api/invitations",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            data=json.dumps({"server_ids": [sample_data["server_id"]]}),
        )
        assert response.status_code == 201

        response_data = response.get_json()
        assert response_data["invitation"]["duration"] == "unlimited"
        assert response_data["invitation"]["unlimited"]
        # Test that URL is included
        assert "url" in response_data["invitation"]
        assert response_data["invitation"]["url"].startswith("/j/")

    def test_create_invitation_requires_server_ids(self, client, api_key, sample_data):
        """Test that server_ids is now required for invitation creation."""
        data = {
            "expires_in_days": 7,
            "duration": "30",
            "unlimited": False,
            "library_ids": [sample_data["library_id"]],
        }

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

    def test_delete_invitation_unauthorized(self, client, sample_data):
        """Test invitation deletion without authentication."""
        response = client.delete(f"/api/invitations/{sample_data['invitation_id']}")
        assert response.status_code == 401

    def test_delete_invitation_success(self, client, api_key, sample_data):
        """Test successful invitation deletion."""
        invitation_id = sample_data["invitation_id"]

        response = client.delete(
            f"/api/invitations/{invitation_id}", headers={"X-API-Key": api_key}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert "message" in data
        assert "deleted successfully" in data["message"]

    def test_delete_invitation_not_found(self, client, api_key):
        """Test deletion of non-existent invitation."""
        response = client.delete(
            "/api/invitations/99999", headers={"X-API-Key": api_key}
        )
        assert response.status_code == 404


class TestAPILibraries:
    """Test the API libraries endpoints."""

    def test_list_libraries_unauthorized(self, client):
        """Test libraries list without authentication."""
        response = client.get("/api/libraries")
        assert response.status_code == 401

    def test_list_libraries_success(self, client, api_key, sample_data):
        """Test successful libraries list."""
        response = client.get("/api/libraries", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        data = response.get_json()
        assert "libraries" in data
        assert "count" in data
        assert data["count"] == len(data["libraries"])

        # Check library data structure
        if data["libraries"]:
            library = data["libraries"][0]
            assert "id" in library
            assert "name" in library
            assert "server_id" in library
            assert library["name"] == "Movies"


class TestAPIServers:
    """Test the API servers endpoints."""

    def test_list_servers_unauthorized(self, client):
        """Test servers list without authentication."""
        response = client.get("/api/servers")
        assert response.status_code == 401

    def test_list_servers_success(self, client, api_key, sample_data):
        """Test successful servers list."""
        response = client.get("/api/servers", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        data = response.get_json()
        assert "servers" in data
        assert "count" in data
        assert data["count"] == len(data["servers"])

        # Check server data structure
        if data["servers"]:
            server = data["servers"][0]
            assert "id" in server
            assert "name" in server
            assert "server_type" in server
            assert "server_url" in server
            assert "external_url" in server
            assert "verified" in server
            assert "allow_downloads" in server
            assert "allow_live_tv" in server
            assert "allow_mobile_uploads" in server
            assert "created_at" in server
            assert server["name"] == "Test Plex Server"
            assert server["server_type"] == "plex"


class TestAPIKeyManagement:
    """Test API key management through the API endpoints."""

    def test_list_api_keys_unauthorized(self, client):
        """Test API keys list without authentication."""
        response = client.get("/api/api-keys")
        assert response.status_code == 401

    def test_list_api_keys_success(self, client, api_key):
        """Test successful API keys list."""
        response = client.get("/api/api-keys", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        data = response.get_json()
        assert "api_keys" in data
        assert "count" in data
        assert data["count"] >= 1  # At least our test key

        # Check that key values are not exposed
        if data["api_keys"]:
            key_data = data["api_keys"][0]
            assert "id" in key_data
            assert "name" in key_data
            assert "created_at" in key_data
            assert "key_hash" not in key_data  # Should not expose the actual key

    def test_delete_api_key_via_api_unauthorized(self, client):
        """Test API key deletion without authentication."""
        response = client.delete("/api/api-keys/1")
        assert response.status_code == 401

    def test_delete_api_key_via_api_self_deletion_prevention(
        self, client, api_key, app
    ):
        """Test that API key cannot delete itself."""
        with app.app_context():
            # Get the test API key ID
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            api_key_obj = ApiKey.query.filter_by(key_hash=key_hash).first()

            response = client.delete(
                f"/api/api-keys/{api_key_obj.id}", headers={"X-API-Key": api_key}
            )
            assert response.status_code == 400
            data = response.get_json()
            assert "Cannot delete the API key currently being used" in data["error"]

    def test_delete_api_key_via_api_success(self, client, api_key, app):
        """Test successful API key deletion via API."""
        with app.app_context():
            # Create another API key to delete
            admin = AdminAccount.query.first()
            raw_key_2 = "test_api_key_to_delete"
            key_hash_2 = hashlib.sha256(raw_key_2.encode()).hexdigest()

            api_key_2 = ApiKey(
                name="Test API Key to Delete",
                key_hash=key_hash_2,
                created_by_id=admin.id,
                is_active=True,
            )
            db.session.add(api_key_2)
            db.session.commit()

            # Delete the second key using the first key
            response = client.delete(
                f"/api/api-keys/{api_key_2.id}", headers={"X-API-Key": api_key}
            )
            assert response.status_code == 200

            data = response.get_json()
            assert "deleted successfully" in data["message"]

            # Verify the key is marked as inactive
            db.session.refresh(api_key_2)
            assert not api_key_2.is_active

    def test_api_key_last_used_updated(self, client, api_key):
        """Test that API key last_used_at is updated when used."""
        with client.application.app_context():
            # Get initial last_used_at
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            api_key_obj = ApiKey.query.filter_by(key_hash=key_hash).first()
            initial_last_used = api_key_obj.last_used_at

            # Make an API call
            response = client.get("/api/status", headers={"X-API-Key": api_key})
            assert response.status_code == 200

            # Check that last_used_at was updated
            db.session.refresh(api_key_obj)
            assert api_key_obj.last_used_at != initial_last_used
            assert api_key_obj.last_used_at is not None


class TestAPIErrorHandling:
    """Test API error handling."""

    def test_malformed_json(self, client, api_key, sample_data):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/invitations",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            data="invalid json",
        )
        # Should return 400 error due to malformed JSON (and missing server_ids)
        assert response.status_code == 400

    def test_missing_content_type(self, client, api_key, sample_data):
        """Test handling when Content-Type is missing for JSON endpoints."""
        response = client.post(
            "/api/invitations",
            headers={"X-API-Key": api_key},
            data=json.dumps(
                {"duration": "30", "server_ids": [sample_data["server_id"]]}
            ),
        )
        # Should still work or return appropriate error
        assert response.status_code in [200, 201, 400, 415]

    def test_api_key_authentication_with_inactive_key(self, client, app):
        """Test that inactive API keys are rejected."""
        with app.app_context():
            admin = AdminAccount.query.first()
            raw_key = "inactive_test_key"
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

            api_key = ApiKey(
                name="Inactive Test Key",
                key_hash=key_hash,
                created_by_id=admin.id,
                is_active=False,  # Inactive key
            )
            db.session.add(api_key)
            db.session.commit()

            response = client.get("/api/status", headers={"X-API-Key": raw_key})
            assert response.status_code == 401
            data = response.get_json()
            assert (
                data["error"] == "Unauthorized"
            )  # Status endpoint uses different error message
