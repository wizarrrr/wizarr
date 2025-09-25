"""
Historical data import service for Plus features.

This service handles importing historical viewing data from media servers
like Plex into the existing ActivitySession model for unified analytics.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.models import MediaServer, db


class HistoricalDataService:
    """Service for importing and managing historical viewing data."""

    def __init__(self, server_id: int):
        self.server_id = server_id
        self.media_server = MediaServer.query.get(server_id)
        if not self.media_server:
            raise ValueError(f"Media server {server_id} not found")

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

            imported_sessions = []
            for entry in history_entries:
                try:
                    activity_session = self._process_plex_history_entry(entry)
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

    def _process_plex_history_entry(self, entry):
        """Process a single Plex history entry into ActivitySession format."""
        try:
            from plus.activity.models import ActivitySession

            # Extract user data
            user_name = getattr(entry, "accountName", "Unknown User")
            user_id = str(getattr(entry, "accountID", "unknown"))

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
            duration_ms = getattr(entry, "duration", 0) or 0
            view_offset = getattr(entry, "viewOffset", 0) or 0
            progress_percent = 0.0

            if duration_ms and view_offset and duration_ms > 0 and view_offset > 0:
                progress_percent = min(
                    100.0, max(0.0, (view_offset / duration_ms) * 100)
                )

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
                started_at=viewed_at,
                ended_at=viewed_at,  # Historical data - mark as completed
                duration_ms=duration_ms,
                final_position_ms=view_offset,
                progress_percent=progress_percent,
            )

            # Set metadata
            activity_session.set_metadata(metadata)

            return activity_session

        except Exception as e:
            logging.warning(f"Failed to process Plex history entry: {e}")
            return None

    def _store_activity_sessions(self, sessions: list) -> int:
        """Store activity sessions in the database."""
        try:
            from plus.activity.models import ActivitySession

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
            from plus.activity.models import ActivitySession

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
            from plus.activity.models import ActivitySession

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
