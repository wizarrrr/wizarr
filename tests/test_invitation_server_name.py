import pytest
from flask import url_for

from app import create_app
from app.extensions import db
from app.models import AdminAccount, MediaServer, Invitation


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
def test_server(app):
    """Create a test media server."""
    with app.app_context():
        server = MediaServer(
            name="My Jellyfin Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_api_key",
            verified=True
        )
        db.session.add(server)
        db.session.commit()
        return server


@pytest.fixture
def test_invitation(app, test_server):
    """Create a test invitation associated with a server."""
    with app.app_context():
        invitation = Invitation(
            code="TESTCODE123",
            used=False,
            unlimited=False,
            duration="unlimited"
        )
        db.session.add(invitation)
        db.session.flush()  # Get the ID
        
        # Associate with the server using the servers relationship
        invitation.servers.append(test_server)
        db.session.commit()
        
        return invitation


def test_invitation_page_displays_server_name(client, test_invitation, test_server):
    """Test that invitation page displays the correct server name."""
    
    response = client.get(f"/join/{test_invitation.code}")
    
    # Should get the welcome page for jellyfin
    assert response.status_code == 200
    
    # Check that the server name appears in the response
    response_text = response.get_data(as_text=True)
    assert "My Jellyfin Server" in response_text
    assert "You've been invited to join the My Jellyfin Server server!" in response_text


def test_invitation_with_no_server_association_falls_back(client, app):
    """Test invitation with no server association falls back gracefully."""
    
    with app.app_context():
        # Create an invitation without server association
        invitation = Invitation(
            code="NOSERVER123",
            used=False,
            unlimited=False,
            duration="unlimited"
        )
        db.session.add(invitation)
        
        # Create a default server that should be used as fallback
        server = MediaServer(
            name="Default Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="default_key",
            verified=True
        )
        db.session.add(server)
        db.session.commit()
    
    response = client.get("/join/NOSERVER123")
    
    # Should still work and show the fallback server name
    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    assert "Default Server" in response_text


def test_invitation_with_legacy_server_field(client, app):
    """Test invitation that uses the legacy server field works correctly."""
    
    with app.app_context():
        server = MediaServer(
            name="Legacy Server",
            server_type="jellyfin", 
            url="http://localhost:8096",
            api_key="legacy_key",
            verified=True
        )
        db.session.add(server)
        db.session.flush()
        
        # Create invitation with legacy server field set
        invitation = Invitation(
            code="LEGACY123",
            used=False,
            unlimited=False,
            duration="unlimited",
            server_id=server.id  # Use legacy server field
        )
        db.session.add(invitation)
        db.session.commit()
    
    response = client.get("/join/LEGACY123")
    
    # Should work with legacy server field
    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    assert "Legacy Server" in response_text


def test_invitation_with_both_server_associations(client, app):
    """Test invitation that has both legacy and new server associations."""
    
    with app.app_context():
        legacy_server = MediaServer(
            name="Legacy Server",
            server_type="jellyfin",
            url="http://localhost:8096", 
            api_key="legacy_key",
            verified=True
        )
        new_server = MediaServer(
            name="New Server",
            server_type="jellyfin",
            url="http://localhost:8097",
            api_key="new_key",
            verified=True
        )
        db.session.add_all([legacy_server, new_server])
        db.session.flush()
        
        invitation = Invitation(
            code="BOTH123",
            used=False,
            unlimited=False,
            duration="unlimited",
            server_id=legacy_server.id  # Legacy field
        )
        db.session.add(invitation)
        db.session.flush()
        
        # Also add to new servers relationship
        invitation.servers.append(new_server)
        db.session.commit()
    
    response = client.get("/join/BOTH123")
    
    # Should prioritize legacy server field
    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    assert "Legacy Server" in response_text