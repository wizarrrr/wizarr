"""
Media server bootstrap functions for integration testing.

These functions configure fresh media server instances via their APIs,
eliminating the need for manual setup or pre-configured volumes.
"""

import logging
import os
import time
import uuid
from typing import Any

import requests

logger = logging.getLogger(__name__)


def wait_for_service(url: str, timeout: int = 120, check_interval: int = 5) -> bool:
    """Wait for a service to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code < 500:  # Any non-server-error is good
                logger.info(f"Service at {url} is ready")
                return True
        except requests.RequestException:
            pass

        logger.debug(f"Waiting for {url}... ({int(time.time() - start_time)}s)")
        time.sleep(check_interval)

    raise TimeoutError(f"Service at {url} did not become available within {timeout}s")


def bootstrap_jellyfin(base_url: str) -> dict[str, Any]:
    """
    Bootstrap a fresh Jellyfin instance via startup wizard API.

    Returns dict with connection info and admin credentials.
    """
    logger.info(f"Bootstrapping Jellyfin at {base_url}")

    # Wait for startup wizard to be ready
    wait_for_service(f"{base_url}/System/Info/Public")

    # Step 1: Set basic configuration
    config_response = requests.post(
        f"{base_url}/Startup/Configuration",
        json={
            "UICulture": "en-US",
            "MetadataCountryCode": "US",
            "PreferredMetadataLanguage": "en",
        },
    )
    config_response.raise_for_status()

    # Step 2: Create admin user (no auth required during setup)
    admin_username = "testadmin"
    admin_password = "TestPass123!"

    user_response = requests.post(
        f"{base_url}/Startup/User",
        json={"Name": admin_username, "Password": admin_password},
    )
    user_response.raise_for_status()

    # Step 3: Complete startup wizard
    complete_response = requests.post(f"{base_url}/Startup/Complete")
    complete_response.raise_for_status()

    # Step 4: Get authentication token
    auth_response = requests.post(
        f"{base_url}/Users/AuthenticateByName",
        json={"Username": admin_username, "Pw": admin_password},
    )
    auth_response.raise_for_status()

    auth_data = auth_response.json()
    token = auth_data["AccessToken"]

    # Step 5: Create test libraries
    headers = {"Authorization": f"MediaBrowser Token={token}"}

    # Movies library
    movies_response = requests.post(
        f"{base_url}/Library/VirtualFolders",
        params={"name": "Movies", "collectionType": "movies"},
        json={"LibraryOptions": {"PathInfos": [{"Path": "/media/movies"}]}},
        headers=headers,
    )
    movies_response.raise_for_status()

    # TV Shows library
    tv_response = requests.post(
        f"{base_url}/Library/VirtualFolders",
        params={"name": "TV Shows", "collectionType": "tvshows"},
        json={"LibraryOptions": {"PathInfos": [{"Path": "/media/tv"}]}},
        headers=headers,
    )
    tv_response.raise_for_status()

    logger.info("Jellyfin bootstrap completed successfully")

    return {
        "url": base_url,
        "token": token,
        "admin_user": admin_username,
        "admin_pass": admin_password,
        "server_type": "jellyfin",
    }


def bootstrap_plex(base_url: str) -> dict[str, Any]:
    """
    Bootstrap Plex with test account credentials.

    Requires PLEX_TEST_USERNAME and PLEX_TEST_PASSWORD environment variables.
    """
    logger.info(f"Bootstrapping Plex at {base_url}")

    # Get test account credentials from environment
    test_username = os.getenv("PLEX_TEST_USERNAME")
    test_password = os.getenv("PLEX_TEST_PASSWORD")

    if not test_username or not test_password:
        raise ValueError(
            "PLEX_TEST_USERNAME and PLEX_TEST_PASSWORD environment variables required"
        )

    # Wait for Plex to be ready
    wait_for_service(f"{base_url}/identity")

    # Get token from Plex.tv
    client_identifier = str(uuid.uuid4())
    auth_response = requests.post(
        "https://plex.tv/users/sign_in.json",
        data={"username": test_username, "password": test_password},
        headers={
            "X-Plex-Product": "Wizarr-Integration-Tests",
            "X-Plex-Version": "1.0.0",
            "X-Plex-Client-Identifier": client_identifier,
        },
    )
    auth_response.raise_for_status()

    auth_data = auth_response.json()
    token = auth_data["user"]["authToken"]

    # Claim the server
    claim_response = requests.post(f"{base_url}/myplex/claim", params={"token": token})
    claim_response.raise_for_status()

    # Create test libraries
    headers = {"X-Plex-Token": token}

    # Movies library
    movies_response = requests.post(
        f"{base_url}/library/sections",
        params={
            "name": "Test Movies",
            "type": "movie",
            "agent": "tv.plex.agents.movie",
            "scanner": "Plex Movie Scanner",
            "language": "en",
            "location": "/data/movies",
        },
        headers=headers,
    )
    movies_response.raise_for_status()

    # TV Shows library
    tv_response = requests.post(
        f"{base_url}/library/sections",
        params={
            "name": "Test TV Shows",
            "type": "show",
            "agent": "tv.plex.agents.series",
            "scanner": "Plex TV Series Scanner",
            "language": "en",
            "location": "/data/tv",
        },
        headers=headers,
    )
    tv_response.raise_for_status()

    logger.info("Plex bootstrap completed successfully")

    return {"url": base_url, "token": token, "server_type": "plex"}


def bootstrap_emby(base_url: str) -> dict[str, Any]:
    """
    Bootstrap a fresh Emby instance via startup wizard API.
    """
    logger.info(f"Bootstrapping Emby at {base_url}")

    # Wait for Emby to be ready
    wait_for_service(f"{base_url}/emby/System/Info/Public")

    # Step 1: Set basic configuration
    config_response = requests.post(
        f"{base_url}/startup/configuration",
        json={
            "ServerName": "Test Emby Server",
            "EnableAutoLogin": False,
            "UICulture": "en-US",
        },
    )
    config_response.raise_for_status()

    # Step 2: Create admin user
    admin_username = "testadmin"
    admin_password = "TestPass123!"

    user_response = requests.post(
        f"{base_url}/startup/user",
        json={"Name": admin_username, "Password": admin_password},
    )
    user_response.raise_for_status()

    # Step 3: Complete startup
    complete_response = requests.post(f"{base_url}/startup/complete")
    complete_response.raise_for_status()

    # Step 4: Get auth token
    auth_response = requests.post(
        f"{base_url}/emby/Users/AuthenticateByName",
        json={"Username": admin_username, "Password": admin_password},
    )
    auth_response.raise_for_status()

    auth_data = auth_response.json()
    token = auth_data["AccessToken"]

    logger.info("Emby bootstrap completed successfully")

    return {
        "url": base_url,
        "token": token,
        "admin_user": admin_username,
        "admin_pass": admin_password,
        "server_type": "emby",
    }


def bootstrap_audiobookshelf(base_url: str) -> dict[str, Any]:
    """
    Bootstrap AudiobookShelf instance.

    Note: AudiobookShelf typically starts with a simple setup.
    """
    logger.info(f"Bootstrapping AudiobookShelf at {base_url}")

    # Wait for service
    wait_for_service(f"{base_url}/healthcheck")

    # AudiobookShelf usually starts ready-to-use
    # May need initial setup via API in the future

    return {
        "url": base_url,
        "token": None,  # May not need token for basic operations
        "server_type": "audiobookshelf",
    }


def create_test_user(
    server_config: dict[str, Any], username: str, email: str
) -> dict[str, Any]:
    """Create a test user in the given media server."""
    server_type = server_config["server_type"]
    base_url = server_config["url"]
    token = server_config["token"]

    if server_type == "jellyfin":
        headers = {"Authorization": f"MediaBrowser Token={token}"}

        user_response = requests.post(
            f"{base_url}/Users/New",
            json={"Name": username, "Password": "testpass123"},
            headers=headers,
        )
        user_response.raise_for_status()

        return user_response.json()

    if server_type == "plex":
        headers = {"X-Plex-Token": token}

        # Plex user creation is more complex - typically done via Plex.tv
        # For testing, we might skip this or use a simpler approach
        logger.warning("Plex user creation not implemented in bootstrap")
        return {}

    if server_type == "emby":
        headers = {"X-Emby-Token": token}

        user_response = requests.post(
            f"{base_url}/emby/Users/New",
            json={"Name": username, "Password": "testpass123"},
            headers=headers,
        )
        user_response.raise_for_status()

        return user_response.json()

    logger.warning(f"User creation not implemented for {server_type}")
    return {}
