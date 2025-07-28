import hashlib
import pytest
from flask import url_for

from app import create_app
from app.extensions import db
from app.models import AdminAccount, ApiKey


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    
    with app.app_context():
        db.create_all()
        
        # Create a test admin account
        admin = AdminAccount(username="testadmin")
        admin.set_password("testpass")
        db.session.add(admin)
        db.session.commit()
        
        yield app
        
        db.session.remove()
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
            is_active=True
        )
        db.session.add(api_key)
        db.session.commit()
        
        return raw_key


def test_app_creation(app):
    """Test that the app can be created successfully."""
    assert app is not None
    assert app.config["TESTING"] is True


def test_api_status_without_key(client):
    """Test API status endpoint without API key."""
    response = client.get("/api/status")
    assert response.status_code == 401
    assert b"Unauthorized" in response.data


def test_api_status_with_invalid_key(client):
    """Test API status endpoint with invalid API key."""
    response = client.get("/api/status", headers={"X-API-Key": "invalid_key"})
    assert response.status_code == 401
    assert b"Unauthorized" in response.data


def test_api_status_with_valid_key(client, api_key):
    """Test API status endpoint with valid API key."""
    response = client.get("/api/status", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    
    data = response.get_json()
    assert "users" in data
    assert "invites" in data
    assert "pending" in data
    assert "expired" in data


def test_api_users_endpoint(client, api_key):
    """Test API users endpoint."""
    response = client.get("/api/users", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    
    data = response.get_json()
    assert "users" in data
    assert "count" in data
    assert isinstance(data["users"], list)
    assert data["count"] == len(data["users"])


def test_api_invitations_endpoint(client, api_key):
    """Test API invitations endpoint."""
    response = client.get("/api/invitations", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    
    data = response.get_json()
    assert "invitations" in data
    assert "count" in data
    assert isinstance(data["invitations"], list)


def test_api_libraries_endpoint(client, api_key):
    """Test API libraries endpoint."""
    response = client.get("/api/libraries", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    
    data = response.get_json()
    assert "libraries" in data
    assert "count" in data
    assert isinstance(data["libraries"], list)


def test_api_servers_endpoint(client, api_key):
    """Test API servers endpoint."""
    response = client.get("/api/servers", headers={"X-API-Key": api_key})
    assert response.status_code == 200
    
    data = response.get_json()
    assert "servers" in data
    assert "count" in data
    assert isinstance(data["servers"], list)