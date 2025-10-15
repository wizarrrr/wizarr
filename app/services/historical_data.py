"""
Historical data import service for Plus features.

This service handles importing historical viewing data from media servers
like Plex into the existing ActivitySession model for unified analytics.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.models import MediaServer, db
from plus.activity.services.identity_resolution import apply_identity_resolution


class HistoricalDataService:
    """Service for importing and managing historical viewing data."""

    def __init__(self, server_id: int):
        self.server_id = server_id
        self.media_server = MediaServer.query.get(server_id)
        if not self.media_server:
            raise ValueError(f"Media server {server_id} not found")
        # Cache Plex item lookups to avoid repeated API calls when resolving durations
        self._duration_cache: dict[str, int] = {}

    def import_plex_history(
        self, days_back: int = 30, max_results: int = 1000
    ) -> dict[str, Any]:
        """
        Import historical viewing data from Plex.

        Args:
            days_back: Number of days back to import history
            max_results: Maximum number of entries to import

        Returns:
            Dictionary with import results
        """
        if self.media_server.server_type != "plex":
            raise ValueError("Server is not a Plex server")

        try:
            from app.services.media import get_media_client

            client = get_media_client(
                self.media_server.server_type, media_server=self.media_server
            )
            if not hasattr(client, "server"):
                raise ValueError("Plex client not properly configured")

            # Calculate date range
            min_date = datetime.now() - timedelta(days=days_back)

            logging.info(
                f"Importing Plex history for last {days_back} days (max {max_results} entries)"
            )

            # Get history from Plex using direct server connection
            history_entries = client.server.history(
                maxresults=max_results, mindate=min_date
            )

            account_lookup = self._build_plex_account_lookup(client)

            # Reset the cache for each import run so we avoid stale lookups between servers
            self._duration_cache.clear()

            imported_sessions = []
            for entry in history_entries:
                try:
                    activity_session = self._process_plex_history_entry(
                        entry, account_lookup, client
                    )
                    if activity_session:
                        imported_sessions.append(activity_session)
                except Exception as e:
                    logging.warning(f"Failed to process history entry: {e}")
                    continue

            # Store in database
            stored_count = self._store_activity_sessions(imported_sessions)

            return {
                "success": True,
                "total_fetched": len(history_entries),
                "total_processed": len(imported_sessions),
                "total_stored": stored_count,
                "date_range": {
                    "from": min_date.isoformat(),
                    "to": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logging.error(f"Failed to import Plex history: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_fetched": 0,
                "total_processed": 0,
                "total_stored": 0,
            }

    def _build_plex_account_lookup(self, client):
        """Build mapping from Plex account ID to human friendly name."""
        lookup = {}
        try:
            for account in client.server.systemAccounts():
                name = (
                    getattr(account, "name", None)
                    or getattr(account, "username", None)
                    or getattr(account, "title", None)
                    or ""
                )
                lookup[str(getattr(account, "id", ""))] = name or ""
        except Exception as exc:
            logging.debug(f"Unable to build Plex account lookup: {exc}")
        return lookup

    def _process_plex_history_entry(self, entry, account_lookup, client):
        """Process a single Plex history entry into ActivitySession format."""
        try:
            from plus.activity.domain.models import ActivitySession

            # Extract user data with multiple fallbacks because Plex history differs by server version
            account = getattr(entry, "account", None)
            user_name = None
            user_id = None

            if account is not None:
                user_name = getattr(account, "title", None) or getattr(
                    account, "name", None
                )
                user_id = getattr(account, "id", None)

            if not user_name:
                user_name = getattr(entry, "accountName", None) or getattr(
                    entry, "username", None
                )
            if not user_id:
                user_id = getattr(entry, "accountID", None) or getattr(
                    entry, "userID", None
                )

            user_id = str(user_id or getattr(entry, "accountID", "unknown"))
            mapped_name = account_lookup.get(user_id)
            if mapped_name:
                user_name = mapped_name
            user_name = user_name or mapped_name or "Unknown User"

            # Extract media data
            media_title = getattr(entry, "title", "Unknown Media")
            media_type = getattr(entry, "type", "unknown").lower()
            media_id = str(getattr(entry, "ratingKey", ""))

            # Handle episodes - extract series info
            series_name = None
            season_number = None
            episode_number = None

            if media_type == "episode":
                series_name = getattr(entry, "grandparentTitle", "")
                season_number = getattr(entry, "parentIndex", None)
                episode_number = getattr(entry, "index", None)

                # Keep original episode title for media_title
                media_title = getattr(entry, "title", "Unknown Episode")

            # Extract viewing time
            viewed_at = getattr(entry, "viewedAt", None)
            if viewed_at is None:
                return None

            if isinstance(viewed_at, int):
                viewed_at = datetime.fromtimestamp(viewed_at, UTC)
            elif not viewed_at.tzinfo:
                viewed_at = viewed_at.replace(tzinfo=UTC)

            # Extract duration and progress with null safety
            duration_ms, duration_source = self._extract_duration(entry, client)

            raw_view_offset = getattr(entry, "viewOffset", None)
            if raw_view_offset is None:
                raw_view_offset = 0
            view_offset = max(int(raw_view_offset or 0), 0)

            # Estimate session start/end times using view_offset (Plex provides end time in viewed_at)
            if duration_ms > 0:
                started_at = viewed_at - timedelta(milliseconds=duration_ms)
            elif view_offset > 0:
                started_at = viewed_at - timedelta(milliseconds=view_offset)
            else:
                started_at = viewed_at

            # Generate unique session ID for historical data
            session_id = f"historical_{getattr(entry, 'ratingKey', 'unknown')}_{user_id}_{int(viewed_at.timestamp())}"

            # Create metadata
            metadata = {
                "plex_rating_key": getattr(entry, "ratingKey", None),
                "plex_parent_rating_key": getattr(entry, "parentRatingKey", None),
                "plex_grandparent_rating_key": getattr(
                    entry, "grandparentRatingKey", None
                ),
                "library_name": getattr(entry, "librarySectionTitle", None),
                "imported_from": "plex_history",
                "import_timestamp": datetime.now(UTC).isoformat(),
                "historical_viewed_at": viewed_at.isoformat(),
                "status": "ended",
                "historical_duration_source": duration_source,
                "historical_duration_ms": duration_ms or None,
            }

            # Create ActivitySession for historical data
            # Mark as ended session since it's historical
            activity_session = ActivitySession(
                server_id=self.server_id,
                session_id=session_id,
                user_name=user_name,
                user_id=user_id,
                media_title=media_title,
                media_type=media_type,
                media_id=media_id,
                series_name=series_name,
                season_number=season_number,
                episode_number=episode_number,
                started_at=started_at,
                active=False,
                duration_ms=duration_ms,
            )

            # Set metadata
            activity_session.set_metadata(metadata)

            if apply_identity_resolution:
                try:
                    apply_identity_resolution(activity_session)
                except Exception as exc:
                    logging.debug(
                        f"Identity resolution failed for historical entry: {exc}"
                    )

            return activity_session

        except Exception as e:
            logging.warning(f"Failed to process Plex history entry: {e}")
            return None

    def _extract_duration(self, entry, client) -> tuple[int, str]:
        """Best-effort extraction of media duration for Plex history items."""
        duration_sources = [
            ("duration", "history_entry_duration"),
            ("parentDuration", "history_parent_duration"),
            ("grandparentDuration", "history_grandparent_duration"),
            ("originalDuration", "history_original_duration"),
        ]

        for attr, source in duration_sources:
            value = getattr(entry, attr, None)
            if isinstance(value, (int, float)) and value > 0:
                return int(value), source

        # Inspect raw metadata if available
        metadata = getattr(entry, "_data", None)
        if isinstance(metadata, dict):
            for key in ("duration", "originalDuration"):
                value = metadata.get(key)
                if isinstance(value, (int, float)) and value > 0:
                    return int(value), f"history_metadata_{key}"

        rating_key = getattr(entry, "ratingKey", None)
        if rating_key:
            cached = self._duration_cache.get(str(rating_key))
            if cached:
                return cached, "cached_item_duration"

            try:
                item = client.server.fetchItem(rating_key)
            except Exception as exc:
                logging.debug(
                    "Unable to fetch Plex item %s for duration lookup: %s",
                    rating_key,
                    exc,
                )
            else:
                for attr, source in (
                    ("duration", "item_duration"),
                    ("originalDuration", "item_original_duration"),
                ):
                    value = getattr(item, attr, None)
                    if isinstance(value, (int, float)) and value > 0:
                        ms_value = int(value)
                        self._duration_cache[str(rating_key)] = ms_value
                        return ms_value, source
                # Cache negative result to avoid repeated lookups for the same key
                self._duration_cache[str(rating_key)] = 0

        return 0, "unknown"

    def _store_activity_sessions(self, sessions: list) -> int:
        """Store activity sessions in the database."""
        try:
            from plus.activity.domain.models import ActivitySession

            stored_count = 0
            for session in sessions:
                try:
                    # Check if session already exists to avoid duplicates
                    existing = ActivitySession.query.filter_by(
                        session_id=session.session_id, server_id=session.server_id
                    ).first()

                    if not existing:
                        db.session.add(session)
                        stored_count += 1

                except Exception as e:
                    logging.warning(f"Failed to store activity session: {e}")
                    continue

            db.session.commit()
            return stored_count

        except Exception as e:
            logging.error(f"Failed to store activity sessions: {e}")
            db.session.rollback()
            return 0

    def get_import_statistics(self) -> dict[str, Any]:
        """Get statistics about imported historical data."""
        try:
            from plus.activity.domain.models import ActivitySession

            # Get basic counts for imported historical data
            imported_query = ActivitySession.query.filter(
                ActivitySession.server_id == self.server_id,
                ActivitySession.session_metadata.like(
                    '%"imported_from": "plex_history"%'
                ),
            )

            total_entries = imported_query.count()
            unique_users = (
                db.session.query(ActivitySession.user_id)
                .filter(
                    ActivitySession.server_id == self.server_id,
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "plex_history"%'
                    ),
                )
                .distinct()
                .count()
            )

            # Get date range
            oldest_entry = imported_query.order_by(
                ActivitySession.started_at.asc()
            ).first()
            newest_entry = imported_query.order_by(
                ActivitySession.started_at.desc()
            ).first()

            return {
                "total_entries": total_entries,
                "unique_users": unique_users,
                "date_range": {
                    "oldest": oldest_entry.started_at.isoformat()
                    if oldest_entry
                    else None,
                    "newest": newest_entry.started_at.isoformat()
                    if newest_entry
                    else None,
                },
            }

        except Exception as e:
            logging.error(f"Failed to get import statistics: {e}")
            return {
                "total_entries": 0,
                "unique_users": 0,
                "date_range": {"oldest": None, "newest": None},
            }

    def clear_historical_data(self) -> dict[str, Any]:
        """Clear all imported historical data for this server."""
        try:
            from plus.activity.domain.models import ActivitySession

            # Delete only imported historical data, not live activity data
            deleted_count = ActivitySession.query.filter(
                ActivitySession.server_id == self.server_id,
                ActivitySession.session_metadata.like(
                    '%"imported_from": "plex_history"%'
                ),
            ).count()

            ActivitySession.query.filter(
                ActivitySession.server_id == self.server_id,
                ActivitySession.session_metadata.like(
                    '%"imported_from": "plex_history"%'
                ),
            ).delete(synchronize_session=False)

            db.session.commit()

            return {"success": True, "deleted_count": deleted_count}

        except Exception as e:
            logging.error(f"Failed to clear historical data: {e}")
            db.session.rollback()
            return {"success": False, "error": str(e), "deleted_count": 0}
