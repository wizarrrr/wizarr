"""Shared utilities for media server clients."""

import datetime
import logging

from app.models import Library
from app.services.media.user_details import MediaUserDetails, UserLibraryAccess


class StandardizedPermissions:
    """Helper class for standardized permission mapping."""

    def __init__(self, server_type: str):
        self.server_type = server_type
        self.is_admin = False
        self.allow_downloads = False
        self.allow_live_tv = False
        self.allow_camera_upload = False

    @classmethod
    def for_plex(cls, plex_user) -> "StandardizedPermissions":
        """Extract standardized permissions from Plex user."""
        perms = cls("plex")
        perms.is_admin = getattr(plex_user, "admin", False)
        perms.allow_downloads = getattr(plex_user, "allowSync", True)
        perms.allow_live_tv = getattr(plex_user, "allowChannels", True)
        perms.allow_camera_upload = getattr(plex_user, "allowCameraUpload", False)
        return perms

    @classmethod
    def for_jellyfin(cls, policy: dict) -> "StandardizedPermissions":
        """Extract standardized permissions from Jellyfin/Emby policy."""
        perms = cls("jellyfin")
        perms.is_admin = policy.get("IsAdministrator", False)
        perms.allow_downloads = policy.get("EnableContentDownloading", False)
        perms.allow_live_tv = policy.get("EnableLiveTvAccess", False)
        perms.allow_camera_upload = False  # Not supported
        return perms

    @classmethod
    def for_audiobookshelf(
        cls, permissions: dict, user_type: str = "user"
    ) -> "StandardizedPermissions":
        """Extract standardized permissions from AudiobookShelf.

        Args:
            permissions: The permissions dict from the user object
            user_type: The user type ("root", "admin", or "user")
        """
        perms = cls("audiobookshelf")
        # AudiobookShelf admin status comes from user.type, not permissions.admin
        perms.is_admin = user_type in ("root", "admin")
        perms.allow_downloads = permissions.get("download", False)
        perms.allow_live_tv = False  # Not supported
        perms.allow_camera_upload = False  # Not supported
        return perms

    @classmethod
    def for_navidrome(cls, raw_user: dict) -> "StandardizedPermissions":
        """Extract standardized permissions from Navidrome user."""
        perms = cls("navidrome")
        perms.is_admin = raw_user.get("adminRole", False)
        perms.allow_downloads = raw_user.get("downloadRole", True)
        perms.allow_live_tv = False  # Not supported
        perms.allow_camera_upload = False  # Not supported
        return perms

    @classmethod
    def for_basic_server(
        cls, server_type: str, is_admin: bool = False, allow_downloads: bool = True
    ) -> "StandardizedPermissions":
        """Create basic permissions for servers without complex permission systems."""
        perms = cls(server_type)
        perms.is_admin = is_admin
        perms.allow_downloads = allow_downloads
        perms.allow_live_tv = False
        perms.allow_camera_upload = False
        return perms


class LibraryAccessHelper:
    """Helper for handling library access patterns."""

    @staticmethod
    def create_restricted_access(
        enabled_libraries: list[str], server_id: int
    ) -> list[UserLibraryAccess]:
        """Create library access list for restricted users."""
        if not enabled_libraries:
            return []

        libs_q = (
            Library.query.filter(
                Library.external_id.in_(enabled_libraries),
                Library.server_id == server_id,
            )
            .order_by(Library.name)
            .all()
        )

        return [
            UserLibraryAccess(
                library_id=lib.external_id, library_name=lib.name, has_access=True
            )
            for lib in libs_q
        ]

    @staticmethod
    def create_full_access() -> None:
        """Return None to indicate full access to all libraries."""
        return  # Full access indicator for standardized system

    @staticmethod
    def create_from_sections(
        sections: list[str], server_id: int
    ) -> list[UserLibraryAccess] | None:
        """Create library access from section names (Plex-style)."""
        if not sections:
            return None  # Full access

        # Try to match sections with database libraries
        libs_q = (
            Library.query.filter(
                Library.name.in_(sections),
                Library.server_id == server_id,
            )
            .order_by(Library.name)
            .all()
        )

        library_access = [
            UserLibraryAccess(
                library_id=lib.external_id, library_name=lib.name, has_access=True
            )
            for lib in libs_q
        ]

        # If no DB matches, create from section names directly
        if not library_access and sections:
            library_access = [
                UserLibraryAccess(
                    library_id=f"section_{i}", library_name=section, has_access=True
                )
                for i, section in enumerate(sections)
            ]

        return library_access or None


class DateHelper:
    """Helper for parsing common date formats."""

    @staticmethod
    def parse_iso_date(date_str: str | None) -> datetime.datetime | None:
        """Parse ISO 8601 date string, handling common variations."""
        if not date_str:
            return None

        try:
            # Handle different ISO formats
            if date_str.endswith("Z"):
                date_str = date_str.rstrip("Z")

            # Handle microseconds
            if "." in date_str:
                # Remove microseconds if present
                date_str = date_str.split(".")[0]

            return datetime.datetime.fromisoformat(date_str)
        except (ValueError, AttributeError) as e:
            logging.warning(f"Failed to parse date '{date_str}': {e}")
            return None

    @staticmethod
    def parse_timestamp(timestamp: int | float | None) -> datetime.datetime | None:
        """Parse Unix timestamp (seconds or milliseconds)."""
        if not timestamp:
            return None

        try:
            # Handle milliseconds timestamp
            if timestamp > 1e10:  # Likely milliseconds
                timestamp = timestamp / 1000

            return datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)
        except (ValueError, OSError) as e:
            logging.warning(f"Failed to parse timestamp '{timestamp}': {e}")
            return None


def create_standardized_user_details(
    user_id: str,
    username: str,
    email: str | None,
    permissions: StandardizedPermissions,
    library_access: list[UserLibraryAccess] | None,
    created_at: datetime.datetime | None = None,
    last_active: datetime.datetime | None = None,
    is_enabled: bool = True,
) -> MediaUserDetails:
    """Create a standardized MediaUserDetails object."""
    return MediaUserDetails(
        user_id=user_id,
        username=username,
        email=email,
        is_admin=permissions.is_admin,
        is_enabled=is_enabled,
        created_at=created_at,
        last_active=last_active,
        allow_downloads=permissions.allow_downloads,
        allow_live_tv=permissions.allow_live_tv,
        allow_camera_upload=permissions.allow_camera_upload,
        library_access=library_access,
    )
