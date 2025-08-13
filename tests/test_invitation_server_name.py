import pytest

from app.extensions import db
from app.models import AdminAccount, Invitation, MediaServer, Settings


@pytest.fixture
def test_server(app):
    """Create a test media server."""
    with app.app_context():
        # Create a test admin account if it doesn't exist
        admin = AdminAccount.query.filter_by(username="testadmin").first()
        if not admin:
            admin = AdminAccount(username="testadmin")
            admin.set_password("testpass")
            db.session.add(admin)

        # Create admin_username setting (required by middleware)
        admin_setting = Settings.query.filter_by(key="admin_username").first()
        if not admin_setting:
            admin_setting = Settings(key="admin_username", value="testadmin")
            db.session.add(admin_setting)

        server = MediaServer(
            name="My Jellyfin Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_api_key",
            verified=True,
        )
        db.session.add(server)
        db.session.commit()
        # Refresh to make sure it's attached
        db.session.refresh(server)
        return server


@pytest.fixture
def test_invitation(app, test_server):
    """Create a test invitation associated with a server."""
    with app.app_context():
        invitation = Invitation(
            code="TESTCODE12",  # 10 characters - within valid range
            used=False,
            unlimited=False,
            duration="unlimited",
        )
        db.session.add(invitation)
        db.session.flush()  # Get the ID

        # Associate with the server using the servers relationship
        invitation.servers.append(test_server)
        db.session.commit()
        # Refresh to make sure it's attached
        db.session.refresh(invitation)
        return invitation


@pytest.fixture
def invitation_no_server(app):
    """Create an invitation without server association."""
    with app.app_context():
        # Create admin_username setting (required by middleware)
        admin_setting = Settings.query.filter_by(key="admin_username").first()
        if not admin_setting:
            admin_setting = Settings(key="admin_username", value="testadmin")
            db.session.add(admin_setting)

        # Create an invitation without server association
        invitation = Invitation(
            code="NOSERVER12",  # 10 characters - within valid range
            used=False,
            unlimited=False,
            duration="unlimited",
        )
        db.session.add(invitation)

        # Create a default server that should be used as fallback
        server = MediaServer(
            name="Default Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="default_key",
            verified=True,
        )
        db.session.add(server)
        db.session.commit()

        return invitation


@pytest.fixture
def legacy_server_invitation(app):
    """Create an invitation that uses the legacy server field."""
    with app.app_context():
        # Create admin_username setting (required by middleware)
        admin_setting = Settings.query.filter_by(key="admin_username").first()
        if not admin_setting:
            admin_setting = Settings(key="admin_username", value="testadmin")
            db.session.add(admin_setting)

        server = MediaServer(
            name="Legacy Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="legacy_key",
            verified=True,
        )
        db.session.add(server)
        db.session.flush()

        # Create invitation with legacy server field set
        invitation = Invitation(
            code="LEGACY1234",  # 10 characters - within valid range
            used=False,
            unlimited=False,
            duration="unlimited",
            server_id=server.id,  # Use legacy server field
        )
        db.session.add(invitation)
        db.session.commit()

        return invitation


@pytest.fixture
def mixed_server_invitation(app):
    """Create an invitation that has both legacy and new server associations."""
    with app.app_context():
        # Create admin_username setting (required by middleware)
        admin_setting = Settings.query.filter_by(key="admin_username").first()
        if not admin_setting:
            admin_setting = Settings(key="admin_username", value="testadmin")
            db.session.add(admin_setting)

        legacy_server = MediaServer(
            name="Legacy Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="legacy_key",
            verified=True,
        )
        new_server = MediaServer(
            name="New Server",
            server_type="jellyfin",
            url="http://localhost:8097",
            api_key="new_key",
            verified=True,
        )
        db.session.add_all([legacy_server, new_server])
        db.session.flush()

        invitation = Invitation(
            code="BOTHCODE12",  # 10 characters - within valid range
            used=False,
            unlimited=False,
            duration="unlimited",
            server_id=legacy_server.id,  # Legacy field
        )
        db.session.add(invitation)
        db.session.flush()

        # Also add to new servers relationship
        invitation.servers.append(new_server)
        db.session.commit()

        return invitation


def test_invitation_page_displays_server_name(client, test_invitation, test_server):
    """Test that invitation page displays the correct server name."""

    response = client.get(f"/j/{test_invitation.code}")

    # Should get the welcome page for jellyfin
    assert response.status_code == 200

    # Check that the server name appears in the response
    response_text = response.get_data(as_text=True)
    assert "My Jellyfin Server" in response_text
    assert "You've been invited to join the My Jellyfin Server server!" in response_text


def test_invitation_with_no_server_association_falls_back(client, invitation_no_server):
    """Test invitation with no server association falls back gracefully."""

    response = client.get("/j/NOSERVER12")

    # Should still work and show some server name (could be any server as fallback)
    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    # Just verify that the invitation page is working with some server name
    # The specific server name depends on test execution order
    assert "Set up Account" in response_text
    assert "You've been invited to join" in response_text


def test_invitation_with_legacy_server_field(client, legacy_server_invitation):
    """Test invitation that uses the legacy server field works correctly."""

    response = client.get("/j/LEGACY1234")

    # Should work with legacy server field
    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    assert "Legacy Server" in response_text


def test_invitation_with_both_server_associations(client, mixed_server_invitation):
    """Test invitation that has both legacy and new server associations."""

    response = client.get("/j/BOTHCODE12")

    # Should prioritize many-to-many relationship over legacy server field
    assert response.status_code == 200
    response_text = response.get_data(as_text=True)
    # The many-to-many servers relationship takes precedence, so we should see "New Server"
    assert "New Server" in response_text
