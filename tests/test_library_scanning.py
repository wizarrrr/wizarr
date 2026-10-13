import hashlib
from unittest.mock import patch

import pytest

from app.models import ApiKey, Library, MediaServer

SCAN = "app.services.media.service.scan_libraries_for_server"


@pytest.fixture
def api_key(session, admin_user):
    """Create a test API key."""
    raw_key = "test_api_key_12345"
    session.add(
        ApiKey(
            name="Test API Key",
            key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
            created_by_id=admin_user.id,
            is_active=True,
        )
    )
    session.commit()
    return raw_key


@pytest.fixture
def test_server(session):
    """Create a test media server."""
    server = MediaServer(
        name="Test Server",
        server_type="jellyfin",
        url="http://localhost:8096",
        api_key="test_api_key",
        verified=True,
    )
    session.add(server)
    session.commit()
    return server


def test_api_libraries_without_existing_libraries(client, api_key, test_server):
    """Test that API libraries endpoint scans when no libraries exist."""
    mock_libraries = {"lib1": "Movies", "lib2": "TV Shows", "lib3": "Music"}

    with patch(SCAN, return_value=(mock_libraries, True)) as mock_scan:
        response = client.get("/api/libraries", headers={"X-API-Key": api_key})

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 3
    assert {lib["name"] for lib in data["libraries"]} == {"Movies", "TV Shows", "Music"}
    mock_scan.assert_called_once()


def test_api_libraries_with_existing_libraries(client, session, api_key, test_server):
    """Test that API libraries endpoint doesn't scan when libraries already exist."""
    session.add_all(
        [
            Library(
                external_id="existing1",
                name="Existing Movies",
                server_id=test_server.id,
            ),
            Library(
                external_id="existing2", name="Existing TV", server_id=test_server.id
            ),
        ]
    )
    session.commit()

    with patch(SCAN) as mock_scan:
        response = client.get("/api/libraries", headers={"X-API-Key": api_key})

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2
    mock_scan.assert_not_called()


def test_api_libraries_scan_failure_continues(client, session, api_key, test_server):
    """Test that API libraries endpoint continues even if one server scan fails."""
    session.add(
        MediaServer(
            name="Test Server 2",
            server_type="plex",
            url="http://localhost:32400",
            api_key="test_api_key_2",
            verified=True,
        )
    )
    session.commit()

    def side_effect(server):
        if server.name == "Test Server":
            raise Exception("Connection failed")
        return {"lib1": "Movies"}, True

    with patch(SCAN, side_effect=side_effect) as mock_scan:
        response = client.get("/api/libraries", headers={"X-API-Key": api_key})

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 1
    assert data["libraries"][0]["server_name"] == "Test Server 2"
    assert mock_scan.call_count == 2
