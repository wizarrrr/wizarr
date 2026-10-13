"""Tests for the Flask-RESTX API endpoints."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.models import ApiKey, Invitation, Library, MediaServer, Settings, User

API_KEY = "test_api_key_12345"


def _add_api_key(session, admin, raw_key, *, name="Test API Key", is_active=True):
    key = ApiKey(
        name=name,
        key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
        created_by_id=admin.id,
        is_active=is_active,
    )
    session.add(key)
    session.commit()
    return key


@pytest.fixture
def api_key(session, admin_user):
    """An active API key. The fixture returns the raw key."""
    _add_api_key(session, admin_user, API_KEY)
    return API_KEY


@pytest.fixture
def sample_data(session):
    """One server, one library, one user and one pending invitation."""
    server = MediaServer(
        name="Test Plex Server",
        server_type="plex",
        url="http://localhost:32400",
        api_key="test_plex_key",
        verified=True,
    )
    session.add(server)
    session.flush()

    library = Library(external_id="1", name="Movies", server_id=server.id)
    user = User(
        token="test_user_token",
        username="testuser",
        email="test@example.com",
        code="ABC123",
        expires=datetime.now(UTC) + timedelta(days=30),
        server_id=server.id,
    )
    invitation = Invitation(
        code="INV123",
        expires=datetime.now(UTC) + timedelta(days=7),
        duration="30",
        unlimited=False,
        server_id=server.id,
    )
    session.add_all([library, user, invitation])
    session.commit()

    return {
        "server_id": server.id,
        "library_id": library.id,
        "user_id": user.id,
        "invitation_id": invitation.id,
    }


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/status"),
        ("get", "/api/users"),
        ("delete", "/api/users/1"),
        ("post", "/api/users/1/extend"),
        ("get", "/api/admins"),
        ("get", "/api/invitations"),
        ("post", "/api/invitations"),
        ("delete", "/api/invitations/1"),
        ("get", "/api/libraries"),
        ("get", "/api/servers"),
        ("get", "/api/api-keys"),
        ("delete", "/api/api-keys/1"),
    ],
)
def test_endpoint_requires_api_key(client, session, method, path):
    response = getattr(client, method)(path, json={"server_ids": [1], "days": 30})
    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


@pytest.mark.parametrize("is_active", [None, False], ids=["unknown", "inactive"])
def test_status_rejects_unknown_or_inactive_key(client, session, admin_user, is_active):
    if is_active is not None:
        _add_api_key(session, admin_user, "rejected_key", is_active=is_active)

    response = client.get("/api/status", headers={"X-API-Key": "rejected_key"})

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_status_with_valid_key(client, api_key, sample_data):
    response = client.get("/api/status", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    assert response.get_json() == {
        "users": 1,
        "invites": 1,
        "pending": 1,
        "expired": 0,
    }


def test_api_key_last_used_updated(client, session, api_key):
    key = ApiKey.query.filter_by(
        key_hash=hashlib.sha256(api_key.encode()).hexdigest()
    ).one()
    assert key.last_used_at is None

    response = client.get("/api/status", headers={"X-API-Key": api_key})

    assert response.status_code == 200
    session.refresh(key)
    assert key.last_used_at is not None


class TestAPIUsers:
    def test_list_users_success(self, client, api_key, sample_data):
        response = client.get("/api/users", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        data = response.get_json()
        assert data["count"] == 1
        user = data["users"][0]
        assert user["id"] == sample_data["user_id"]
        assert user["username"] == "testuser"
        assert user["email"] == "test@example.com"
        assert user["server"] == "Test Plex Server"
        assert user["server_type"] == "plex"

    def test_delete_user_not_found(self, client, api_key):
        response = client.delete("/api/users/99999", headers={"X-API-Key": api_key})
        assert response.status_code == 404
        assert response.get_json()["error"] == "User not found"

    def test_extend_user_expiry_success(self, client, session, api_key, sample_data):
        user = session.get(User, sample_data["user_id"])
        old_expiry = user.expires

        response = client.post(
            f"/api/users/{sample_data['user_id']}/extend",
            headers={"X-API-Key": api_key},
            json={"days": 14},
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["message"] == "User testuser expiry extended by 14 days"
        session.refresh(user)
        assert user.expires == old_expiry + timedelta(days=14)
        assert data["new_expiry"] == user.expires.isoformat()

    def test_extend_user_expiry_not_found(self, client, api_key):
        response = client.post(
            "/api/users/99999/extend",
            headers={"X-API-Key": api_key},
            json={"days": 15},
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "User not found"


def test_list_admins_success(client, api_key, admin_user):
    response = client.get("/api/admins", headers={"X-API-Key": api_key})
    assert response.status_code == 200

    data = response.get_json()
    assert data["count"] == 1
    admin = data["admins"][0]
    assert admin["id"] == admin_user.id
    assert admin["username"] == "testadmin"
    assert admin["passkeys"] == 0
    assert "created" in admin


class TestAPIInvitations:
    def test_list_invitations_success(self, client, api_key, sample_data):
        response = client.get("/api/invitations", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        data = response.get_json()
        assert data["count"] == 1
        invitation = data["invitations"][0]
        assert invitation["id"] == sample_data["invitation_id"]
        assert invitation["code"] == "INV123"
        assert invitation["status"] == "pending"
        assert invitation["url"] == "/j/INV123"
        assert invitation["duration"] == "30"
        assert {"created", "expires"} <= invitation.keys()

    def test_list_invitations_returns_relative_url_for_loopback_host(
        self, client, api_key, sample_data
    ):
        """The invitation URL must not contain an internal loopback host."""
        response = client.get(
            "/api/invitations",
            headers={"X-API-Key": api_key, "Host": "127.0.0.1:5690"},
        )
        assert response.status_code == 200

        invitation = response.get_json()["invitations"][0]
        assert invitation["url"] == f"/j/{invitation['code']}"

    def test_invitation_with_global_setting(self, client, session, api_key):
        """A custom global display name replaces the server name."""
        server = MediaServer(
            name="Actual Server Name",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_key",
            verified=True,
        )
        invitation = Invitation(
            code="GLOBALSETTING", used=False, unlimited=False, duration="unlimited"
        )
        invitation.servers.append(server)
        session.add_all(
            [Settings(key="server_name", value="My Custom Media Center"), invitation]
        )
        session.commit()

        response = client.get("/api/invitations", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        invite_data = response.get_json()["invitations"][0]
        assert invite_data["display_name"] == "My Custom Media Center"
        assert invite_data["server_names"] == ["Actual Server Name"]
        assert invite_data["uses_global_setting"] is True

    def test_create_invitation_success(self, client, api_key, sample_data):
        response = client.post(
            "/api/invitations",
            headers={"X-API-Key": api_key},
            json={
                "server_ids": [sample_data["server_id"]],
                "expires_in_days": 7,
                "duration": "30",
                "unlimited": False,
                "library_ids": [sample_data["library_id"]],
            },
        )
        assert response.status_code == 201

        data = response.get_json()
        assert data["message"] == "Invitation created successfully"
        invitation = data["invitation"]
        assert invitation["duration"] == "30"
        assert invitation["unlimited"] is False
        assert invitation["url"] == f"/j/{invitation['code']}"
        assert invitation["server_names"] == ["Test Plex Server"]
        assert invitation["display_name"] == "Test Plex Server"
        assert invitation["uses_global_setting"] is False

    def test_create_invitation_default_values(self, client, api_key, sample_data):
        response = client.post(
            "/api/invitations",
            headers={"X-API-Key": api_key},
            json={"server_ids": [sample_data["server_id"]]},
        )
        assert response.status_code == 201

        invitation = response.get_json()["invitation"]
        assert invitation["duration"] == "unlimited"
        assert invitation["unlimited"] is True
        assert invitation["expires"] is None
        assert invitation["url"] == f"/j/{invitation['code']}"

    def test_create_invitation_requires_server_ids(self, client, api_key, sample_data):
        response = client.post(
            "/api/invitations",
            headers={"X-API-Key": api_key},
            json={
                "expires_in_days": 7,
                "duration": "30",
                "unlimited": False,
                "library_ids": [sample_data["library_id"]],
            },
        )
        assert response.status_code == 400

        data = response.get_json()
        assert "Server selection is required" in data["error"]
        assert data["available_servers"] == [
            {
                "id": sample_data["server_id"],
                "name": "Test Plex Server",
                "server_type": "plex",
            }
        ]

    def test_create_invitation_with_malformed_json(self, client, api_key, sample_data):
        response = client.post(
            "/api/invitations",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            data="invalid json",
        )
        assert response.status_code == 400
        assert Invitation.query.count() == 1

    def test_delete_invitation_success(self, client, session, api_key, sample_data):
        response = client.delete(
            f"/api/invitations/{sample_data['invitation_id']}",
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        assert (
            response.get_json()["message"] == "Invitation INV123 deleted successfully"
        )
        assert session.get(Invitation, sample_data["invitation_id"]) is None

    def test_delete_invitation_not_found(self, client, api_key):
        response = client.delete(
            "/api/invitations/99999", headers={"X-API-Key": api_key}
        )
        assert response.status_code == 404
        assert response.get_json()["error"] == "Invitation not found"


def test_list_libraries_success(client, api_key, sample_data):
    response = client.get("/api/libraries", headers={"X-API-Key": api_key})
    assert response.status_code == 200

    data = response.get_json()
    assert data["count"] == 1
    library = data["libraries"][0]
    assert library["id"] == sample_data["library_id"]
    assert library["name"] == "Movies"
    assert library["external_id"] == "1"
    assert library["server_id"] == sample_data["server_id"]
    assert library["server_name"] == "Test Plex Server"


def test_list_servers_success(client, api_key, sample_data):
    response = client.get("/api/servers", headers={"X-API-Key": api_key})
    assert response.status_code == 200

    data = response.get_json()
    assert data["count"] == 1
    server = data["servers"][0]
    assert server["id"] == sample_data["server_id"]
    assert server["name"] == "Test Plex Server"
    assert server["server_type"] == "plex"
    assert server["server_url"] == "http://localhost:32400"
    assert server["verified"] is True
    assert {
        "external_url",
        "allow_downloads",
        "allow_live_tv",
        "allow_mobile_uploads",
        "created_at",
    } <= server.keys()


class TestAPIKeyManagement:
    def test_list_api_keys_success(self, client, api_key):
        response = client.get("/api/api-keys", headers={"X-API-Key": api_key})
        assert response.status_code == 200

        data = response.get_json()
        assert data["count"] == 1
        key_data = data["api_keys"][0]
        assert key_data["name"] == "Test API Key"
        assert key_data["last_used_at"] is not None
        assert {"id", "created_at"} <= key_data.keys()
        # The API must never expose the key hash.
        assert "key_hash" not in key_data

    def test_delete_api_key_not_found(self, client, api_key):
        response = client.delete("/api/api-keys/99999", headers={"X-API-Key": api_key})
        assert response.status_code == 404
        assert response.get_json()["error"] == "API key not found"

    def test_delete_api_key_cannot_delete_itself(self, client, api_key):
        key = ApiKey.query.filter_by(
            key_hash=hashlib.sha256(api_key.encode()).hexdigest()
        ).one()

        response = client.delete(
            f"/api/api-keys/{key.id}", headers={"X-API-Key": api_key}
        )

        assert response.status_code == 400
        assert (
            response.get_json()["error"]
            == "Cannot delete the API key currently being used"
        )
        assert key.is_active is True

    def test_delete_api_key_success(self, client, session, admin_user, api_key):
        other_key = _add_api_key(
            session, admin_user, "test_api_key_to_delete", name="Key to Delete"
        )

        response = client.delete(
            f"/api/api-keys/{other_key.id}", headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        assert (
            response.get_json()["message"]
            == "API key 'Key to Delete' deleted successfully"
        )
        session.refresh(other_key)
        assert other_key.is_active is False
