"""Standardized user details data structures for media clients."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class UserLibraryAccess:
    """User's access to a specific library."""

    library_id: str
    library_name: str
    has_access: bool = True


@dataclass(frozen=True)
class MediaUserDetails:
    """Standardized user details returned by media clients."""

    user_id: str
    username: str
    email: str | None = None
    is_admin: bool = False
    is_enabled: bool = True
    created_at: datetime | None = None
    last_active: datetime | None = None

    # Library access - None means "all libraries"
    library_access: list[UserLibraryAccess] | None = None

    # Server-specific policy/configuration data
    raw_policies: dict[str, Any] | None = None

    @property
    def has_library_restrictions(self) -> bool:
        """True if user has specific library restrictions, False if full access."""
        return self.library_access is not None

    @property
    def accessible_library_names(self) -> list[str]:
        """Get list of library names user can access."""
        if self.library_access is None:
            return []  # Full access - caller should get all server libraries
        return [lib.library_name for lib in self.library_access if lib.has_access]
