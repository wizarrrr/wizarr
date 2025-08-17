"""
Mock implementations for media server APIs used in invitation testing.

These mocks simulate the behavior of external media server APIs (Plex, Jellyfin, etc.)
to enable testing of invitation flows without requiring actual server instances.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import Mock


@dataclass
class MockUser:
    """Represents a user in a mock media server."""

    id: str
    username: str
    email: str
    enabled: bool = True
    libraries: list[str] = field(default_factory=list)
    policy: dict[str, Any] = field(default_factory=dict)


@dataclass
class MockLibrary:
    """Represents a library in a mock media server."""

    id: str
    name: str
    type: str
    enabled: bool = True


class MockMediaServerState:
    """Shared state for mock media servers to simulate persistent data."""

    def __init__(self):
        self.users: dict[str, MockUser] = {}
        self.libraries: dict[str, MockLibrary] = {
            "lib1": MockLibrary("lib1", "Movies", "movie"),
            "lib2": MockLibrary("lib2", "TV Shows", "show"),
            "lib3": MockLibrary("lib3", "Music", "artist"),
        }
        self.connection_healthy = True
        self.api_key_valid = True
        self.create_user_failures = []  # List of usernames that should fail

    def reset(self):
        """Reset state for fresh tests."""
        self.users.clear()
        self.connection_healthy = True
        self.api_key_valid = True
        self.create_user_failures.clear()


# Global state instance for sharing across mock clients
mock_state = MockMediaServerState()


class MockJellyfinClient:
    """Mock Jellyfin client that simulates API responses."""

    def __init__(self, url: str = None, token: str = None, **kwargs):
        self.url = url or "http://localhost:8096"
        self.token = token or "mock-api-key"
        self.server_id = kwargs.get("server_id")

    def _create_user_with_identity_linking(self, user_kwargs: dict):
        """Mock version of the database user creation."""
        from app.extensions import db
        from app.models import User

        # Check if this is part of a multi-server invitation
        code = user_kwargs.get("code")
        if code:
            existing_user = User.query.filter_by(code=code).first()
            if existing_user and existing_user.identity_id:
                # Link to existing identity from same invitation
                user_kwargs["identity_id"] = existing_user.identity_id

        new_user = User(**user_kwargs)
        db.session.add(new_user)
        db.session.flush()  # Get the ID immediately
        return new_user

    def validate_connection(self) -> tuple[bool, str]:
        """Simulate connection validation."""
        if not mock_state.connection_healthy:
            return False, "Connection failed"
        if not mock_state.api_key_valid:
            return False, "Invalid API key"
        return True, "Connection successful"

    def libraries(self) -> dict[str, str]:
        """Return mock library mapping."""
        return {
            lib.name: lib.id for lib in mock_state.libraries.values() if lib.enabled
        }

    def create_user(self, username: str, password: str) -> str:
        """Simulate user creation and return user ID."""
        if username in mock_state.create_user_failures:
            raise Exception(f"Failed to create user {username}")

        user_id = str(uuid.uuid4())
        mock_state.users[user_id] = MockUser(
            id=user_id,
            username=username,
            email="",  # Set later
        )
        return user_id

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get user details."""
        if user_id not in mock_state.users:
            raise Exception(f"User {user_id} not found")

        user = mock_state.users[user_id]
        return {
            "Id": user.id,
            "Name": user.username,
            "Primary": user.email,
            "Policy": user.policy,
            "Configuration": {
                "DisplayMissingEpisodes": False,
                "GroupedFolders": [],
                "SubtitleMode": "Default",
                "EnableLocalPassword": True,
            },
        }

    def set_policy(self, user_id: str, policy: dict[str, Any]) -> None:
        """Update user policy."""
        if user_id in mock_state.users:
            mock_state.users[user_id].policy.update(policy)

    def _set_specific_folders(self, user_id: str, library_ids: list[str]) -> None:
        """Set library access for user."""
        if user_id in mock_state.users:
            mock_state.users[user_id].libraries = library_ids

    def get(self, endpoint: str):
        """Mock HTTP GET requests."""
        response_mock = Mock()
        if "/Users/" in endpoint:
            user_id = endpoint.split("/Users/")[1]
            try:
                response_mock.json.return_value = self.get_user(user_id)
            except Exception:
                response_mock.json.return_value = {"error": "User not found"}
        else:
            response_mock.json.return_value = {"success": True}
        return response_mock

    def post(self, endpoint: str, **kwargs):
        """Mock HTTP POST requests."""
        response_mock = Mock()
        response_mock.json.return_value = {"success": True}
        return response_mock

    def patch(self, endpoint: str, **kwargs):
        """Mock HTTP PATCH requests."""
        response_mock = Mock()
        response_mock.json.return_value = {"success": True}
        return response_mock

    def delete(self, endpoint: str, **kwargs):
        """Mock HTTP DELETE requests."""
        response_mock = Mock()
        response_mock.json.return_value = {"success": True}
        return response_mock

    def _do_join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        """Mock implementation of invitation join process."""
        # Check connection health first
        if not mock_state.connection_healthy:
            return False, "Connection failed"
        if not mock_state.api_key_valid:
            return False, "Invalid API key"

        # Basic validation
        if password != confirm:
            return False, "Passwords do not match"
        if len(password) < 8:
            return False, "Password too short"
        if username in mock_state.create_user_failures:
            return False, f"Failed to create user {username}"

        try:
            # Simulate user creation in mock state
            user_id = self.create_user(username, password)

            # Set email
            mock_state.users[user_id].email = email

            # Set libraries based on invitation (like real clients do)
            from app.models import Invitation, Library

            inv = Invitation.query.filter_by(code=code).first()
            if inv and inv.libraries:
                # Use invitation-specific libraries
                enabled_libs = [
                    lib.external_id
                    for lib in inv.libraries
                    if lib.server_id == self.server_id
                ]
            else:
                # Use all enabled libraries for server (fallback)
                enabled_libs = (
                    [
                        lib.external_id
                        for lib in Library.query.filter_by(
                            enabled=True, server_id=self.server_id
                        ).all()
                    ]
                    if self.server_id
                    else list(mock_state.libraries.keys())
                )

            self._set_specific_folders(user_id, enabled_libs)

            # Set default policy
            default_policy = {
                "EnableDownloads": True,
                "EnableLiveTvAccess": False,
                "IsAdministrator": False,
            }
            self.set_policy(user_id, default_policy)

            # Create user in database (like real clients do)
            from app.models import Invitation
            from app.services.expiry import calculate_user_expiry

            inv = Invitation.query.filter_by(code=code).first()
            expires = calculate_user_expiry(inv, self.server_id) if inv else None

            self._create_user_with_identity_linking(
                {
                    "username": username,
                    "email": email,
                    "token": user_id,
                    "code": code,
                    "expires": expires,
                    "server_id": self.server_id,
                }
            )

            return True, ""

        except Exception as e:
            return False, str(e)

    def join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        """Public join method that delegates to _do_join."""
        return self._do_join(username, password, confirm, email, code)


class MockPlexClient:
    """Mock Plex client that simulates PlexAPI responses."""

    def __init__(self, url: str = None, token: str = None, **kwargs):
        self.url = url or "http://localhost:32400"
        self.token = token or "mock-plex-token"
        self.server_id = kwargs.get("server_id")

    def _create_user_with_identity_linking(self, user_kwargs: dict):
        """Mock version of the database user creation."""
        from app.extensions import db
        from app.models import User

        # Check if this is part of a multi-server invitation
        code = user_kwargs.get("code")
        if code:
            existing_user = User.query.filter_by(code=code).first()
            if existing_user and existing_user.identity_id:
                # Link to existing identity from same invitation
                user_kwargs["identity_id"] = existing_user.identity_id

        new_user = User(**user_kwargs)
        db.session.add(new_user)
        db.session.flush()  # Get the ID immediately
        return new_user

    def validate_connection(self) -> tuple[bool, str]:
        """Simulate connection validation."""
        if not mock_state.connection_healthy:
            return False, "Plex server unreachable"
        if not mock_state.api_key_valid:
            return False, "Invalid Plex token"
        return True, "Connected to Plex"

    def libraries(self) -> dict[str, str]:
        """Return mock Plex library mapping."""
        return {
            lib.name: lib.id for lib in mock_state.libraries.values() if lib.enabled
        }

    def _do_join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        """Mock Plex invitation join process."""
        # Check connection health first
        if not mock_state.connection_healthy:
            return False, "Plex server unreachable"
        if not mock_state.api_key_valid:
            return False, "Invalid Plex token"

        if password != confirm:
            return False, "Passwords do not match"
        if "@" not in email:
            return False, "Invalid email format"
        if username in mock_state.create_user_failures:
            return False, f"Plex user creation failed for {username}"

        try:
            # Simulate Plex user creation (Plex uses email as identifier)
            user_id = str(uuid.uuid4())
            mock_state.users[user_id] = MockUser(
                id=user_id,
                username=username,
                email=email,
                libraries=list(
                    mock_state.libraries.keys()
                ),  # Plex gets all libraries by default
            )

            # Create user in database (like real clients do)
            from app.models import Invitation
            from app.services.expiry import calculate_user_expiry

            inv = Invitation.query.filter_by(code=code).first()
            expires = calculate_user_expiry(inv, self.server_id) if inv else None

            self._create_user_with_identity_linking(
                {
                    "username": username,
                    "email": email,
                    "token": user_id,
                    "code": code,
                    "expires": expires,
                    "server_id": self.server_id,
                }
            )

            return True, ""

        except Exception as e:
            return False, f"Plex error: {str(e)}"

    def join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        """Public join method that delegates to _do_join."""
        return self._do_join(username, password, confirm, email, code)


class MockAudiobookshelfClient:
    """Mock Audiobookshelf client."""

    def __init__(self, url: str = None, token: str = None, **kwargs):
        self.url = url or "http://localhost:13378"
        self.token = token or "mock-abs-token"
        self.server_id = kwargs.get("server_id")

    def _create_user_with_identity_linking(self, user_kwargs: dict):
        """Mock version of the database user creation."""
        from app.extensions import db
        from app.models import User

        # Check if this is part of a multi-server invitation
        code = user_kwargs.get("code")
        if code:
            existing_user = User.query.filter_by(code=code).first()
            if existing_user and existing_user.identity_id:
                # Link to existing identity from same invitation
                user_kwargs["identity_id"] = existing_user.identity_id

        new_user = User(**user_kwargs)
        db.session.add(new_user)
        db.session.flush()  # Get the ID immediately
        return new_user

    def validate_connection(self) -> tuple[bool, str]:
        if not mock_state.connection_healthy:
            return False, "Audiobookshelf server unreachable"
        return True, "Connected to Audiobookshelf"

    def libraries(self) -> dict[str, str]:
        # Audiobookshelf typically has audiobook and podcast libraries
        return {"audiobooks": "Audiobooks", "podcasts": "Podcasts"}

    def _do_join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        # Check connection health first
        if not mock_state.connection_healthy:
            return False, "Audiobookshelf server unreachable"

        if password != confirm:
            return False, "Passwords do not match"
        if username in mock_state.create_user_failures:
            return False, f"ABS user creation failed for {username}"

        try:
            user_id = str(uuid.uuid4())
            mock_state.users[user_id] = MockUser(
                id=user_id,
                username=username,
                email=email,
                policy={"isActive": True, "canDownload": True},
            )

            # Create user in database (like real clients do)
            from app.models import Invitation
            from app.services.expiry import calculate_user_expiry

            inv = Invitation.query.filter_by(code=code).first()
            expires = calculate_user_expiry(inv, self.server_id) if inv else None

            self._create_user_with_identity_linking(
                {
                    "username": username,
                    "email": email,
                    "token": user_id,
                    "code": code,
                    "expires": expires,
                    "server_id": self.server_id,
                }
            )

            return True, ""

        except Exception as e:
            return False, f"Audiobookshelf error: {str(e)}"

    def join(
        self, username: str, password: str, confirm: str, email: str, code: str
    ) -> tuple[bool, str]:
        """Public join method that delegates to _do_join."""
        return self._do_join(username, password, confirm, email, code)


# Factory function to create mock clients
def create_mock_client(server_type: str, **kwargs):
    """Create appropriate mock client based on server type."""
    mock_clients = {
        "jellyfin": MockJellyfinClient,
        "plex": MockPlexClient,
        "audiobookshelf": MockAudiobookshelfClient,
    }

    client_class = mock_clients.get(server_type.lower())
    if not client_class:
        raise ValueError(f"No mock client available for server type: {server_type}")

    return client_class(**kwargs)


# Helper functions for test setup
def setup_mock_servers():
    """Setup mock servers with realistic data."""
    mock_state.reset()

    # Add some realistic libraries
    mock_state.libraries.update(
        {
            "movies_4k": MockLibrary("movies_4k", "Movies 4K", "movie"),
            "anime": MockLibrary("anime", "Anime", "show"),
            "audiobooks": MockLibrary("audiobooks", "Audiobooks", "audiobook"),
        }
    )


def simulate_server_failure():
    """Simulate server connection failure."""
    mock_state.connection_healthy = False


def simulate_auth_failure():
    """Simulate authentication failure."""
    mock_state.api_key_valid = False


def simulate_user_creation_failure(usernames: list[str]):
    """Simulate user creation failures for specific usernames."""
    mock_state.create_user_failures.extend(usernames)


def get_mock_state():
    """Get current mock state for assertions."""
    return mock_state
