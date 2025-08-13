"""Test server name resolution for invitations."""

import pytest

from app import create_app
from app.config import BaseConfig
from app.extensions import db
from app.models import MediaServer, Settings
from app.services.server_name_resolver import (
    get_display_name_info,
    get_server_names_for_api,
    resolve_invitation_server_name,
)


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
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


class TestServerNameResolver:
    """Test server name resolution logic for invitations."""

    def test_single_server_no_global_setting(self, app):
        """Test single server with no global Display Name setting."""
        with app.app_context():
            server = MediaServer(
                name="My Jellyfin Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key",
                verified=True,
            )
            db.session.add(server)
            db.session.commit()

            # No global setting exists
            result = resolve_invitation_server_name([server])
            assert result == "My Jellyfin Server"

    def test_single_server_with_default_global_setting(self, app):
        """Test single server with default 'Wizarr' global setting."""
        with app.app_context():
            server = MediaServer(
                name="My Jellyfin Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key",
                verified=True,
            )

            # Create default Wizarr setting
            setting = Settings(key="server_name", value="Wizarr")
            db.session.add_all([server, setting])
            db.session.commit()

            # Should fall back to server name when global setting is default
            result = resolve_invitation_server_name([server])
            assert result == "My Jellyfin Server"

    def test_single_server_with_custom_global_setting(self, app):
        """Test single server with custom global Display Name setting."""
        with app.app_context():
            server = MediaServer(
                name="My Jellyfin Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key",
                verified=True,
            )

            # Create custom global setting
            setting = Settings(key="server_name", value="My Custom Media Center")
            db.session.add_all([server, setting])
            db.session.commit()

            # Should use custom global setting
            result = resolve_invitation_server_name([server])
            assert result == "My Custom Media Center"

    def test_multiple_servers_no_global_setting(self, app):
        """Test multiple servers with no global setting."""
        with app.app_context():
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
            db.session.commit()

            # Should list all server names
            result = resolve_invitation_server_name([server1, server2])
            assert result == "Plex Server, Jellyfin Server"

    def test_multiple_servers_with_custom_global_setting(self, app):
        """Test multiple servers with custom global setting."""
        with app.app_context():
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

            # Create custom global setting
            setting = Settings(key="server_name", value="My Home Media Hub")
            db.session.add_all([server1, server2, setting])
            db.session.commit()

            # Should use custom global setting even with multiple servers
            result = resolve_invitation_server_name([server1, server2])
            assert result == "My Home Media Hub"

    def test_empty_servers_list(self, app):
        """Test with empty servers list."""
        with app.app_context():
            result = resolve_invitation_server_name([])
            assert result == "Unknown Server"

    def test_get_display_name_info(self, app):
        """Test comprehensive display name info function."""
        with app.app_context():
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
            db.session.commit()

            info = get_display_name_info([server1, server2])

            assert info["display_name"] == "Plex Server, Jellyfin Server"
            assert info["server_names"] == ["Plex Server", "Jellyfin Server"]
            assert info["uses_global_setting"] is False
            assert info["global_setting_value"] is None

    def test_get_display_name_info_with_global_setting(self, app):
        """Test display name info with global setting."""
        with app.app_context():
            server = MediaServer(
                name="My Server",
                server_type="jellyfin",
                url="http://localhost:8096",
                api_key="test_key",
                verified=True,
            )
            setting = Settings(key="server_name", value="Custom Name")
            db.session.add_all([server, setting])
            db.session.commit()

            info = get_display_name_info([server])

            assert info["display_name"] == "Custom Name"
            assert info["server_names"] == ["My Server"]
            assert info["uses_global_setting"] is True
            assert info["global_setting_value"] == "Custom Name"

    def test_get_server_names_for_api(self, app):
        """Test server names for API responses."""
        with app.app_context():
            server1 = MediaServer(name="Server 1", server_type="plex")
            server2 = MediaServer(name="Server 2", server_type="jellyfin")

            names = get_server_names_for_api([server1, server2])
            assert names == ["Server 1", "Server 2"]

            # Test empty list
            names = get_server_names_for_api([])
            assert names == []
