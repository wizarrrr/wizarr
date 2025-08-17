"""
Mock implementations for testing.

This package provides mock implementations of external services
for testing Wizarr functionality without requiring real services.
"""

from .media_server_mocks import (
    MockAudiobookshelfClient,
    MockJellyfinClient,
    MockPlexClient,
    create_mock_client,
    get_mock_state,
    mock_state,
    setup_mock_servers,
    simulate_auth_failure,
    simulate_server_failure,
    simulate_user_creation_failure,
)

__all__ = [
    "create_mock_client",
    "setup_mock_servers",
    "simulate_server_failure",
    "simulate_auth_failure",
    "simulate_user_creation_failure",
    "get_mock_state",
    "mock_state",
    "MockJellyfinClient",
    "MockPlexClient",
    "MockAudiobookshelfClient",
]
