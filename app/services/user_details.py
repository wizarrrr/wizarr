"""User details service for retrieving extended user information."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast

from app.extensions import db
from app.models import ActivitySession, MediaServer, User
from app.services.media.service import get_client_for_media_server
from app.services.media.user_details import MediaUserDetails


@dataclass(frozen=True)
class AccountInfo:
    """Data transfer object for user account information."""

    server_type: str
    server_name: str
    username: str
    libraries: list[str] | None
    is_admin: bool
    allow_downloads: bool
    allow_live_tv: bool
    allow_camera_upload: bool
    is_inactive: bool = False
    last_activity_date: datetime | None = None


@dataclass(frozen=True)
class UserDetailsDTO:
    """Data transfer object for user details response."""

    user: User
    join_date: datetime | None
    accounts_info: list[AccountInfo]


class UserDetailsService:
    """Service for retrieving extended user information."""

    def get_user_details(self, db_id: int) -> UserDetailsDTO:
        """Retrieve detailed information for a user including linked accounts."""
        user = db.get_or_404(User, db_id)

        join_date = self._get_join_date(user)
        accounts = self._get_linked_accounts(user)
        accounts_info = self._build_accounts_info(accounts)

        return UserDetailsDTO(
            user=user, join_date=join_date, accounts_info=accounts_info
        )

    def _get_join_date(self, user: User) -> datetime | None:
        """Extract the join/creation date from user identity."""
        if user.identity and user.identity.created_at:
            return user.identity.created_at
        return None

    def _get_linked_accounts(self, user: User) -> list[User]:
        """Get all accounts linked to this user's identity."""
        if user.identity_id:
            return list(user.identity.accounts)
        return [user]

    def _build_accounts_info(self, accounts: list[User]) -> list[AccountInfo]:
        """Build account information for each linked account."""
        accounts_info = []

        for account in accounts:
            try:
                info = self._get_account_info(account)
                accounts_info.append(info)
            except Exception as exc:
                logging.error(
                    "Failed to fetch user details for account %s/%s: %s",
                    account.id,
                    account.username,
                    exc,
                )
                # Add a basic info object even if API call failed
                server = account.server
                is_inactive, last_activity = (
                    self.check_user_inactivity(account, server)
                    if server
                    else (False, None)
                )
                accounts_info.append(
                    AccountInfo(
                        server_type=server.server_type if server else "local",
                        server_name=server.name if server else "Local",
                        username=account.username,
                        libraries=None,
                        is_admin=False,
                        allow_downloads=False,
                        allow_live_tv=False,
                        allow_camera_upload=False,
                        is_inactive=is_inactive,
                        last_activity_date=last_activity,
                    )
                )

        return accounts_info

        

    def check_user_inactivity(
        self, account: User, server: MediaServer
        ) -> tuple[bool, datetime | None]:
        """Check if user is inactive based on server's inactivity threshold.

        Returns:
            Tuple of (is_inactive, last_activity_date)
        """
        
        # If no threshold is set, user is never considered inactive
        if server.inactivity_threshold_days is None:
            return False, self._get_join_date(account)

        # Determine filter for ActivitySession
        session_filter = {"server_id": server.id}

        if account.identity_id:
            session_filter["wizarr_identity_id"] = account.identity_id
        else:
            session_filter["wizarr_user_id"] = account.id

        last_session = (
                db.session.query(ActivitySession)
                .filter_by(**session_filter)
                .order_by(ActivitySession.started_at.desc())
                .first()
            )

        # Use join_date if no activity session exists
        last_activity = last_session.started_at if last_session else self._get_join_date(account)

        # If we still have no date, treat as never active
        if last_activity is None:
            return True, None

        threshold_date = datetime.now() - timedelta(days=server.inactivity_threshold_days)
        is_inactive = last_activity < threshold_date

        return is_inactive, last_activity


    def _get_account_info(self, account: User) -> AccountInfo:
        """Get detailed information for a single account."""
        server: MediaServer | None = cast(MediaServer | None, account.server)

        # Check inactivity status
        is_inactive, last_activity = (
            self.check_user_inactivity(account, server)
            if server
            else (False, None)
        )

        if not server:
            return AccountInfo(
                server_type="local",
                server_name="Local",
                username=account.username,
                libraries=None,
                is_admin=False,
                allow_downloads=False,
                allow_live_tv=False,
                allow_camera_upload=False,
                is_inactive=is_inactive,
                last_activity_date=last_activity,
            )

        # Use standardized metadata if available
        if account.accessible_libraries is not None or account.is_admin is not None:
            # Use standardized metadata columns
            return AccountInfo(
                server_type=server.server_type,
                server_name=server.name,
                username=account.username,
                libraries=account.get_accessible_libraries(),
                is_admin=account.is_admin or False,
                allow_downloads=account.allow_downloads or False,
                allow_live_tv=account.allow_live_tv or False,
                allow_camera_upload=account.allow_camera_upload or False,
                is_inactive=is_inactive,
                last_activity_date=last_activity,
            )

        # No standardized metadata available, fetch from API
        client = get_client_for_media_server(server)

        # All clients now implement get_user_details - use the standardized interface
        user_arg = account.id if server.server_type == "plex" else account.token
        details: MediaUserDetails = client.get_user_details(user_arg)

        libraries = self._extract_libraries_from_details(server, account, details)

        # Update user with standardized metadata for future use
        account.update_standardized_metadata(details)

        return AccountInfo(
            server_type=server.server_type,
            server_name=server.name,
            username=details.username,
            libraries=libraries,
            is_admin=details.is_admin,
            allow_downloads=details.allow_downloads,
            allow_live_tv=details.allow_live_tv,
            allow_camera_upload=details.allow_camera_upload,
            is_inactive=is_inactive,
            last_activity_date=last_activity,
        )

    def _extract_libraries_from_cached_data(
        self, _server: MediaServer, account: User
    ) -> list[str]:
        """Extract library names from cached user data."""
        library_access_data = account.get_library_access()
        if not library_access_data:
            return []

        # Extract library names from cached JSON data
        accessible_libraries = [
            lib.get("library_name", "")
            for lib in library_access_data
            if isinstance(lib, dict) and lib.get("has_access", False)
        ]

        return [name for name in accessible_libraries if name]

    def _extract_libraries_from_details(
        self, server: MediaServer, account: User, details: MediaUserDetails
    ) -> list[str] | None:
        """Extract library names from MediaUserDetails."""
        if getattr(details, "library_access_unknown", False):
            cached = self._extract_libraries_from_cached_data(server, account)
            return cached or []

        # If library_access is None, user has full access
        if details.library_access is None:
            return None

        # Otherwise return the specific accessible library names
        return details.accessible_library_names
