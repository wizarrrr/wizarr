import hashlib
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import AdminAccount, ApiKey, Library, MediaServer, Settings


@pytest.fixture
def api_key(app, session):
    """Create a test API key."""
    with app.app_context():
        # Create admin account if it doesn't exist
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

        db.session.commit()

        raw_key = "test_api_key_12345"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # Check if API key already exists
        existing_key = ApiKey.query.filter_by(key_hash=key_hash).first()
        if not existing_key:
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
def test_server(app, session):
    """Create a test media server."""
    with app.app_context():
        # Create admin account if it doesn't exist
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
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_api_key",
            verified=True,
        )
        db.session.add(server)
        db.session.commit()
        return server


def test_api_libraries_without_existing_libraries(client, api_key, test_server):
    """Test that API libraries endpoint scans when no libraries exist."""

    # Clear any existing libraries first
    with client.application.app_context():
        Library.query.delete()
        db.session.commit()

    # Mock the scan_libraries_for_server function to return test data
    mock_libraries = {"lib1": "Movies", "lib2": "TV Shows", "lib3": "Music"}

    with patch("app.services.media.service.scan_libraries_for_server") as mock_scan:
        mock_scan.return_value = mock_libraries

        response = client.get("/api/libraries", headers={"X-API-Key": api_key})

        assert response.status_code == 200
        data = response.get_json()

        # Should have scanned and found the libraries
        assert "libraries" in data
        assert "count" in data
        # Should have at least the 3 libraries from our mock (may have more from scanning servers)
        assert data["count"] >= 3

        # Verify the library data structure
        libraries = data["libraries"]
        assert len(libraries) >= 3

        # Verify that scan was called at least once
        assert mock_scan.call_count >= 1


def test_api_libraries_with_existing_libraries(client, api_key, test_server):
    """Test that API libraries endpoint doesn't scan when libraries already exist."""

    # Clear any existing libraries first, then create specific test libraries
    with client.application.app_context():
        Library.query.delete()
        db.session.commit()

        # Re-query the server to get it in the current session context
        server = MediaServer.query.filter_by(name="Test Server").first()
        lib1 = Library(
            external_id="existing1", name="Existing Movies", server_id=server.id
        )
        lib2 = Library(external_id="existing2", name="Existing TV", server_id=server.id)
        db.session.add_all([lib1, lib2])
        db.session.commit()

    with patch("app.services.media.service.scan_libraries_for_server") as mock_scan:
        response = client.get("/api/libraries", headers={"X-API-Key": api_key})

        assert response.status_code == 200
        data = response.get_json()

        # Should return existing libraries without scanning
        assert "libraries" in data
        assert "count" in data
        assert data["count"] == 2

        # Verify that scan was NOT called since libraries already exist
        mock_scan.assert_not_called()


def test_api_libraries_scan_failure_continues(client, api_key, test_server):
    """Test that API libraries endpoint continues even if one server scan fails."""

    # Clear any existing libraries to ensure clean test
    with client.application.app_context():
        Library.query.delete()
        db.session.commit()

        # Clear existing servers to avoid conflicts
        MediaServer.query.filter(MediaServer.name.like("Test Server%")).delete()
        db.session.commit()

        # Create our two test servers fresh
        server1 = MediaServer(
            name="Test Server",
            server_type="jellyfin",
            url="http://localhost:8096",
            api_key="test_api_key",
            verified=True,
        )
        server2 = MediaServer(
            name="Test Server 2",
            server_type="plex",
            url="http://localhost:32400",
            api_key="test_api_key_2",
            verified=True,
        )
        db.session.add_all([server1, server2])
        db.session.commit()

    # Mock scan to fail for first server but succeed for second
    mock_libraries = {"lib1": "Movies"}

    def side_effect(server):
        if server.name == "Test Server":
            raise Exception("Connection failed")
        return mock_libraries

    with patch("app.services.media.service.scan_libraries_for_server") as mock_scan:
        mock_scan.side_effect = side_effect

        response = client.get("/api/libraries", headers={"X-API-Key": api_key})

        assert response.status_code == 200
        data = response.get_json()

        # Should succeed despite one server failing
        assert "libraries" in data
        assert "count" in data
        # Should have at least the library from the successful server
        assert data["count"] >= 1

        # Should have tried to scan servers
        assert mock_scan.call_count >= 2


def _login(client, admin_id):
    """Establish a Flask-Login session for the given admin account."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_id)
        sess["_fresh"] = True


def test_rescan_preserves_disabled_libraries(client, test_server):
    """A re-scan must not silently re-enable libraries the admin deselected.

    Regression test: scan_server_libraries() used to set ``enabled = True`` on
    every library returned by the media server, on every scan. Because the
    library checkbox partial renders ``{% if lib.enabled %}checked{% endif %}``,
    that quietly undid the admin's selection each time they re-scanned.
    """
    with client.application.app_context():
        Library.query.delete()
        db.session.commit()

        server = MediaServer.query.filter_by(name="Test Server").first()
        db.session.add_all(
            [
                Library(
                    external_id="lib1",
                    name="Movies",
                    server_id=server.id,
                    enabled=True,
                ),
                Library(
                    external_id="lib2",
                    name="TV Shows",
                    server_id=server.id,
                    enabled=False,  # admin deselected this one
                ),
            ]
        )
        db.session.commit()

        admin = AdminAccount.query.filter_by(username="testadmin").first()
        admin_id, server_id = admin.id, server.id

    _login(client, admin_id)

    # The server still reports both libraries on the next scan.
    with patch(
        "app.blueprints.media_servers.routes.scan_libraries_for_server"
    ) as mock_scan:
        mock_scan.return_value = {"lib1": "Movies", "lib2": "TV Shows"}

        response = client.post(f"/settings/servers/{server_id}/scan-libraries")
        assert response.status_code == 200

    with client.application.app_context():
        enabled_by_ext = {
            lib.external_id: lib.enabled
            for lib in Library.query.filter_by(server_id=server_id).all()
        }

    assert enabled_by_ext["lib1"] is True, "selected library should stay selected"
    assert enabled_by_ext["lib2"] is False, (
        "deselected library must stay deselected across a re-scan"
    )
