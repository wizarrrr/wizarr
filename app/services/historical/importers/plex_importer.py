"""Plex historical data importer."""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.models import ActivitySession, HistoricalImportJob

logger = structlog.get_logger(__name__)


class PlexHistoricalImporter:
    """Handles importing historical viewing data from Plex servers."""

    def __init__(self, server_id: int, media_server):
        self.server_id = server_id
        self.media_server = media_server
        self._duration_cache: dict[str, int] = {}

    def import_history(
        self,
        days_back: int,
        max_results: int | None,
        job_id: int | None,
        update_job_callback=None,
    ) -> dict[str, Any]:
        """
        Import historical viewing data from Plex.

        Args:
            days_back: Number of days back to import history
            max_results: Maximum number of entries to import (None for unlimited)
            job_id: Optional job identifier for progress updates
            update_job_callback: Callback to update job progress

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
            min_date = datetime.now(UTC) - timedelta(days=days_back)

            logger.info(
                "plex_import_started",
                days_back=days_back,
                max_results=max_results,
            )

            # Get history from Plex
            history_kwargs = {"mindate": min_date}
            if max_results:
                history_kwargs["maxresults"] = max_results

            history_entries = client.server.history(**history_kwargs)
            total_entries = len(history_entries)

            if job_id is not None and update_job_callback:
                update_job_callback(
                    job_id,
                    status=HistoricalImportJob.STATUS_RUNNING,
                    total_fetched=total_entries,
                    total_processed=0,
                    total_stored=0,
                    error_message=None,
                )

            account_lookup = self._build_account_lookup(client)
            self._duration_cache.clear()

            imported_sessions = []
            for entry in history_entries:
                try:
                    activity_session = self._process_history_entry(
                        entry, account_lookup, client
                    )
                    if activity_session:
                        imported_sessions.append(activity_session)
                        if (
                            job_id is not None
                            and len(imported_sessions) % 25 == 0
                            and update_job_callback
                        ):
                            update_job_callback(
                                job_id,
                                total_processed=len(imported_sessions),
                            )
                except Exception as e:
                    logger.warning("entry_process_failed", error=str(e))
                    continue

            return {
                "success": True,
                "sessions": imported_sessions,
                "total_fetched": total_entries,
                "total_processed": len(imported_sessions),
                "date_range": {
                    "from": min_date.isoformat(),
                    "to": datetime.now(UTC).isoformat(),
                },
            }

        except Exception as e:
            logger.error("plex_import_failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "sessions": [],
                "total_fetched": 0,
                "total_processed": 0,
            }

    def _build_account_lookup(self, client) -> dict[str, str]:
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
            logger.debug("account_lookup_failed", error=str(exc))
        return lookup

    def _process_history_entry(
        self, entry, account_lookup, client
    ) -> ActivitySession | None:
        """Process a single Plex history entry into ActivitySession format."""
        try:
            # Extract user data
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

            if isinstance(user_name, str):
                user_name = user_name.strip()
            user_name = user_name or "Unknown User"

            # Extract media data
            raw_title = getattr(entry, "title", None)
            if isinstance(raw_title, str):
                raw_title = raw_title.strip()
            media_title = raw_title or "Unknown Media"
            media_type = getattr(entry, "type", "unknown").lower()
            media_id = str(getattr(entry, "ratingKey", ""))

            # Handle episodes
            series_name = None
            season_number = None
            episode_number = None

            if media_type == "episode":
                series_raw = getattr(entry, "grandparentTitle", None)
                if isinstance(series_raw, str):
                    series_raw = series_raw.strip()
                series_name = series_raw or None
                season_number = getattr(entry, "parentIndex", None)
                episode_number = getattr(entry, "index", None)

                episode_title = getattr(entry, "title", None)
                if isinstance(episode_title, str):
                    episode_title = episode_title.strip()
                media_title = episode_title or media_title or "Unknown Episode"

            if not media_title:
                media_title = "Unknown Media"

            # Extract viewing time
            viewed_at = getattr(entry, "viewedAt", None)
            if viewed_at is None:
                return None

            if isinstance(viewed_at, int):
                viewed_at = datetime.fromtimestamp(viewed_at, UTC)
            elif not viewed_at.tzinfo:
                viewed_at = viewed_at.replace(tzinfo=UTC)

            # Extract duration
            duration_ms, duration_source = self._extract_duration(entry, client)

            raw_view_offset = getattr(entry, "viewOffset", None)
            if raw_view_offset is None:
                raw_view_offset = 0
            view_offset = max(int(raw_view_offset or 0), 0)

            # Calculate start time
            if duration_ms > 0:
                started_at = viewed_at - timedelta(milliseconds=duration_ms)
            elif view_offset > 0:
                started_at = viewed_at - timedelta(milliseconds=view_offset)
            else:
                started_at = viewed_at

            # Generate session ID
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

            # Create ActivitySession
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

            activity_session.set_metadata(metadata)

            try:
                from app.services.activity.identity_resolution import (
                    apply_identity_resolution,
                )

                if apply_identity_resolution:
                    apply_identity_resolution(activity_session)
            except Exception as exc:
                logger.debug(
                    "identity_resolution_failed",
                    error=str(exc),
                )

            return activity_session

        except Exception as e:
            logger.warning("plex_entry_process_failed", error=str(e))
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

        # Inspect raw metadata
        metadata = getattr(entry, "_data", None)
        if isinstance(metadata, dict):
            for key in ("duration", "originalDuration"):
                value = metadata.get(key)
                if isinstance(value, (int, float)) and value > 0:
                    return int(value), f"history_metadata_{key}"

        # Try fetching from server
        rating_key = getattr(entry, "ratingKey", None)
        if rating_key:
            cached = self._duration_cache.get(str(rating_key))
            if cached:
                return cached, "cached_item_duration"

            try:
                item = client.server.fetchItem(rating_key)
            except Exception as exc:
                logger.debug(
                    "item_fetch_failed",
                    rating_key=rating_key,
                    error=str(exc),
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
                self._duration_cache[str(rating_key)] = 0

        return 0, "unknown"
