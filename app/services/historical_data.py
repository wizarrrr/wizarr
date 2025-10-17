"""
Historical data import service for Wizarr.

This service handles importing historical viewing data from media servers
like Plex into the existing ActivitySession model for unified analytics.
"""

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app

from app.models import HistoricalImportJob, MediaServer, db
from app.services.activity.identity_resolution import apply_identity_resolution


class HistoricalDataService:
    """Service for importing and managing historical viewing data."""

    def __init__(self, server_id: int):
        self.server_id = server_id
        self.media_server = MediaServer.query.get(server_id)
        if not self.media_server:
            raise ValueError(f"Media server {server_id} not found")
        # Cache Plex item lookups to avoid repeated API calls when resolving durations
        self._duration_cache: dict[str, int] = {}

    def start_async_import(self, days_back: int, max_results: int | None = None):
        """
        Launch a background job to import Plex history data.
        """
        job = HistoricalImportJob(
            server_id=self.server_id,
            days_back=days_back,
            max_results=max_results,
            status=HistoricalImportJob.STATUS_QUEUED,
        )
        db.session.add(job)
        db.session.commit()

        app = current_app._get_current_object()

        worker = threading.Thread(
            target=self._run_import_job,
            args=(app, job.id, self.server_id, days_back, max_results),
            name=f"historical-import-{job.id}",
            daemon=True,
        )
        worker.start()

        return job

    def import_history(
        self,
        days_back: int = 30,
        max_results: int | None = 1000,
        job_id: int | None = None,
    ) -> dict[str, Any]:
        """Dispatch historical import based on server type."""
        server_type = (self.media_server.server_type or "").lower()

        if server_type == "plex":
            return self._import_plex_history(
                days_back=days_back, max_results=max_results, job_id=job_id
            )
        if server_type in {"jellyfin", "emby"}:
            return self._import_jellyfin_history(
                days_back=days_back, max_results=max_results, job_id=job_id
            )
        if server_type == "audiobookshelf":
            return self._import_audiobookshelf_history(
                days_back=days_back, max_results=max_results, job_id=job_id
            )

        raise ValueError(f"Historical import not supported for {server_type!r}")

    def import_plex_history(
        self,
        days_back: int = 30,
        max_results: int | None = 1000,
        job_id: int | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible Plex history import entry point."""
        return self._import_plex_history(
            days_back=days_back, max_results=max_results, job_id=job_id
        )

    def _import_plex_history(
        self,
        days_back: int,
        max_results: int | None,
        job_id: int | None,
    ) -> dict[str, Any]:
        """
        Import historical viewing data from Plex.

        Args:
            days_back: Number of days back to import history
            max_results: Maximum number of entries to import (None for unlimited)
            job_id: Optional job identifier for progress updates

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
            history_kwargs = {"mindate": min_date}
            if max_results:
                history_kwargs["maxresults"] = max_results

            history_entries = client.server.history(**history_kwargs)
            total_entries = len(history_entries)

            if job_id is not None:
                self._update_job(
                    job_id,
                    status=HistoricalImportJob.STATUS_RUNNING,
                    total_fetched=total_entries,
                    total_processed=0,
                    total_stored=0,
                    error_message=None,
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
                        if job_id is not None and len(imported_sessions) % 25 == 0:
                            self._update_job(
                                job_id,
                                total_processed=len(imported_sessions),
                            )
                except Exception as e:
                    logging.warning(f"Failed to process history entry: {e}")
                    continue

            # Store in database
            stored_count = self._store_activity_sessions(
                imported_sessions, job_id=job_id
            )

            if job_id is not None:
                self._update_job(
                    job_id,
                    total_processed=len(imported_sessions),
                    total_stored=stored_count,
                )

            return {
                "success": True,
                "total_fetched": total_entries,
                "total_processed": len(imported_sessions),
                "total_stored": stored_count,
                "date_range": {
                    "from": min_date.isoformat(),
                    "to": datetime.now().isoformat(),
                },
            }

        except Exception as e:
            logging.error(f"Failed to import Plex history: {e}")
            if job_id is not None:
                self._update_job(
                    job_id,
                    status=HistoricalImportJob.STATUS_FAILED,
                    error_message=str(e),
                )
            return {
                "success": False,
                "error": str(e),
                "total_fetched": 0,
                "total_processed": 0,
                "total_stored": 0,
            }

    def _import_jellyfin_history(
        self,
        days_back: int,
        max_results: int | None,
        job_id: int | None,
    ) -> dict[str, Any]:
        """Import historical playback data from Jellyfin/Emby servers."""
        from app.services.media import get_media_client

        client = get_media_client(
            self.media_server.server_type, media_server=self.media_server
        )

        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        logging.info(
            "%s historical import: collecting last %s days (limit=%s)",
            self.media_server.server_type.title(),
            days_back,
            max_results or "unlimited",
        )

        try:
            users_response = client.get("/Users").json()
        except Exception as exc:
            logging.error("Failed to fetch Jellyfin users: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "total_fetched": 0,
                "total_processed": 0,
                "total_stored": 0,
            }

        imported_sessions: list[Any] = []
        total_seen = 0
        entries_seen = 0
        total_record_count: int | None = None

        def maybe_stop() -> bool:
            return max_results is not None and total_seen >= max_results

        for user in users_response:
            if maybe_stop():
                break

            user_id = user.get("Id")
            if not user_id:
                continue

            user_name = (user.get("Name") or "Unknown").strip() or "Unknown"
            start_index = 0
            page_size = 100
            exhausted = False
            user_sessions_before = len(imported_sessions)

            while not exhausted and not maybe_stop():
                params = {
                    "Filters": "IsPlayed",
                    "SortBy": "DatePlayed",
                    "SortOrder": "Descending",
                    "IncludeItemTypes": "Movie,Episode",
                    "Recursive": "true",
                    "StartIndex": start_index,
                    "Limit": page_size,
                    "Fields": "UserData,SeriesInfo,SeasonInfo,BasicSyncInfo",
                }

                try:
                    response = client.get(
                        f"/Users/{user_id}/Items", params=params
                    ).json()
                except Exception as exc:
                    logging.warning(
                        "Failed to fetch history for Jellyfin user %s: %s",
                        user_id,
                        exc,
                    )
                    break

                items = response.get("Items", [])
                if not items:
                    break

                logging.debug(
                    "%s history: user %s fetched %s items at index %s",
                    self.media_server.server_type,
                    user_name,
                    len(items),
                    start_index,
                )

                entries_seen += len(items)
                total_record_count = response.get(
                    "TotalRecordCount", total_record_count
                )

                if job_id is not None and entries_seen % 100 == 0:
                    expected_total = (
                        total_record_count
                        if total_record_count is not None
                        else entries_seen
                    )
                    self._update_job(
                        job_id,
                        total_fetched=expected_total,
                        total_processed=len(imported_sessions),
                    )

                for item in items:
                    if maybe_stop():
                        break

                    user_data = item.get("UserData") or {}
                    last_played_raw = user_data.get("LastPlayedDate")
                    viewed_at = self._parse_datetime(last_played_raw)
                    if viewed_at is None:
                        viewed_at = self._ticks_to_datetime(
                            user_data.get("LastPlayedDateTicks")
                        )
                    if not viewed_at:
                        continue

                    if viewed_at < cutoff:
                        exhausted = True
                        continue

                    duration_ms = self._ticks_to_ms(item.get("RunTimeTicks"))
                    position_ms = self._ticks_to_ms(
                        user_data.get("PlaybackPositionTicks")
                    )

                    started_at = viewed_at
                    if duration_ms and duration_ms > 0:
                        started_at = viewed_at - timedelta(milliseconds=duration_ms)
                    elif position_ms and position_ms > 0:
                        started_at = viewed_at - timedelta(milliseconds=position_ms)

                    media_type = (item.get("Type") or "unknown").lower()
                    media_title = (
                        item.get("Name") or "Unknown Media"
                    ).strip() or "Unknown Media"
                    media_id = str(item.get("Id") or "")
                    series_name = item.get("SeriesName") or None
                    season_number = item.get("ParentIndexNumber")
                    episode_number = item.get("IndexNumber")

                    session_id = (
                        f"{self.media_server.server_type}_history_"
                        f"{media_id}_{user_id}_{int(viewed_at.timestamp())}"
                    )

                    metadata = {
                        "imported_from": f"{self.media_server.server_type}_history",
                        "historical_viewed_at": viewed_at.isoformat(),
                        "historical_duration_ms": duration_ms or None,
                        "historical_play_count": user_data.get("PlayCount"),
                        "historical_position_ms": position_ms or None,
                        "media_source_id": media_id,
                        "historical_duration_source": "runtime_ticks"
                        if duration_ms
                        else None,
                        "historical_user_id": str(user_id),
                    }

                    activity_session = self._build_activity_session(
                        session_id=session_id,
                        user_name=user_name,
                        user_id=str(user_id),
                        media_title=media_title,
                        media_type=media_type,
                        media_id=media_id,
                        series_name=series_name,
                        season_number=season_number,
                        episode_number=episode_number,
                        started_at=started_at,
                        duration_ms=duration_ms,
                        viewed_at=viewed_at,
                        metadata=metadata,
                    )

                    if activity_session:
                        imported_sessions.append(activity_session)
                        total_seen += 1

                        if job_id is not None and total_seen % 25 == 0:
                            self._update_job(
                                job_id,
                                total_fetched=(
                                    total_record_count
                                    if total_record_count is not None
                                    else entries_seen
                                ),
                                total_processed=len(imported_sessions),
                            )

                if maybe_stop() or exhausted:
                    break

                start_index += len(items)
                if len(items) < page_size:
                    break

            if len(imported_sessions) - user_sessions_before > 0:
                logging.debug(
                    "%s history: user %s contributed %s sessions",
                    self.media_server.server_type,
                    user_name,
                    len(imported_sessions) - user_sessions_before,
                )

        stored_count = self._store_activity_sessions(imported_sessions, job_id=job_id)

        if job_id is not None:
            expected_total = (
                total_record_count if total_record_count is not None else entries_seen
            )
            self._update_job(
                job_id,
                total_fetched=expected_total,
                total_processed=len(imported_sessions),
                total_stored=stored_count,
            )

        logging.info(
            "%s historical import complete: %s items inspected, %s sessions stored",
            self.media_server.server_type.title(),
            entries_seen,
            stored_count,
        )

        return {
            "success": True,
            "total_fetched": entries_seen,
            "total_processed": len(imported_sessions),
            "total_stored": stored_count,
            "date_range": {
                "from": cutoff.isoformat(),
                "to": datetime.now(UTC).isoformat(),
            },
        }

    def _import_audiobookshelf_history(
        self,
        days_back: int,
        max_results: int | None,
        job_id: int | None,
    ) -> dict[str, Any]:
        """Import historical listening session data from AudiobookShelf servers."""
        from app.services.media import get_media_client

        client = get_media_client(
            self.media_server.server_type, media_server=self.media_server
        )

        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        logging.info(
            "AudiobookShelf historical import: collecting last %s days (limit=%s)",
            days_back,
            max_results or "unlimited",
        )

        endpoint = f"{client.API_PREFIX}/sessions"
        imported_sessions: list[Any] = []
        total_seen = 0
        entries_seen = 0
        page = 0
        items_per_page = 100
        total_sessions: int | None = None

        def maybe_stop() -> bool:
            return max_results is not None and total_seen >= max_results

        try:
            # Fetch sessions page by page
            while not maybe_stop():
                query_params = {"itemsPerPage": str(items_per_page), "page": str(page)}

                try:
                    response = client.get(endpoint, params=query_params)
                    response.raise_for_status()
                    data = response.json()
                except Exception as exc:
                    logging.warning(
                        "Failed to fetch AudiobookShelf sessions page %s: %s",
                        page,
                        exc,
                    )
                    break

                sessions = data.get("sessions", [])
                if not sessions:
                    break

                total_sessions = data.get("total", total_sessions)
                entries_seen += len(sessions)

                logging.debug(
                    "AudiobookShelf history: fetched %s sessions at page %s",
                    len(sessions),
                    page,
                )

                if job_id is not None and entries_seen % 100 == 0:
                    expected_total = (
                        total_sessions if total_sessions is not None else entries_seen
                    )
                    self._update_job(
                        job_id,
                        total_fetched=expected_total,
                        total_processed=len(imported_sessions),
                    )

                # Process each session
                exhausted = False
                for session in sessions:
                    if maybe_stop() or exhausted:
                        break

                    if not isinstance(session, dict):
                        continue

                    # Get session timestamps
                    updated_at_ms = session.get("updatedAt")
                    started_at_ms = session.get("startedAt")

                    # Parse viewed_at (when session ended or was last updated)
                    viewed_at = None
                    if updated_at_ms:
                        viewed_at = datetime.fromtimestamp(updated_at_ms / 1000, UTC)

                    if not viewed_at:
                        continue

                    # Check if session is within our date range
                    if viewed_at < cutoff:
                        exhausted = True
                        continue

                    # Extract user information
                    user_id = str(session.get("userId", ""))
                    user_info = session.get("user") or {}
                    if not isinstance(user_info, dict):
                        user_info = {}

                    user_name = (
                        user_info.get("username")
                        or user_info.get("displayName")
                        or user_info.get("name")
                        or session.get("userDisplayName")
                        or "Unknown User"
                    )

                    # Extract media information
                    media_title = session.get("displayTitle") or "Unknown Media"
                    media_type = session.get("mediaType", "book")
                    media_id = str(
                        session.get("libraryItemId") or session.get("id", "")
                    )
                    session_id_raw = str(session.get("id", ""))

                    # Calculate duration and position
                    # timeListening is the actual listening duration for this session (in seconds)
                    # duration is the full book/media duration (not what we want here)
                    time_listening_s = session.get("timeListening", 0) or 0
                    current_time_s = session.get("currentTime", 0) or 0

                    # Convert to milliseconds
                    duration_ms = (
                        int(time_listening_s * 1000) if time_listening_s else 0
                    )
                    position_ms = int(current_time_s * 1000)

                    # Calculate started_at
                    if started_at_ms:
                        started_at = datetime.fromtimestamp(started_at_ms / 1000, UTC)
                    elif duration_ms and duration_ms > 0:
                        # Use actual listening duration to calculate start time
                        started_at = viewed_at - timedelta(milliseconds=duration_ms)
                    elif updated_at_ms and started_at_ms:
                        # Fallback: calculate from session timestamps
                        session_duration_ms = updated_at_ms - started_at_ms
                        started_at = viewed_at - timedelta(
                            milliseconds=session_duration_ms
                        )
                    else:
                        started_at = viewed_at

                    # Generate unique session ID
                    session_id = (
                        f"audiobookshelf_history_{session_id_raw}_{user_id}_"
                        f"{int(viewed_at.timestamp())}"
                    )

                    # Build metadata
                    metadata = {
                        "imported_from": "audiobookshelf_history",
                        "historical_viewed_at": viewed_at.isoformat(),
                        "historical_duration_ms": duration_ms or None,
                        "historical_position_ms": position_ms or None,
                        "media_source_id": media_id,
                        "historical_duration_source": "time_listening",  # Actual session duration
                        "historical_user_id": str(user_id),
                        "abs_session_id": session_id_raw,
                        "play_method": session.get("playMethod"),
                        "time_listening_seconds": time_listening_s,  # Store original value for reference
                    }

                    # Add device info if available
                    device_info = session.get("deviceInfo")
                    if device_info:
                        metadata["device_info"] = device_info

                    activity_session = self._build_activity_session(
                        session_id=session_id,
                        user_name=user_name,
                        user_id=user_id,
                        media_title=media_title,
                        media_type=media_type,
                        media_id=media_id,
                        series_name=None,  # AudiobookShelf doesn't track series in sessions
                        season_number=None,
                        episode_number=None,
                        started_at=started_at,
                        duration_ms=duration_ms,
                        viewed_at=viewed_at,
                        metadata=metadata,
                    )

                    if activity_session:
                        imported_sessions.append(activity_session)
                        total_seen += 1

                        if job_id is not None and total_seen % 25 == 0:
                            self._update_job(
                                job_id,
                                total_fetched=(
                                    total_sessions
                                    if total_sessions is not None
                                    else entries_seen
                                ),
                                total_processed=len(imported_sessions),
                            )

                if exhausted:
                    break

                # Check if we've fetched all pages
                page += 1
                if len(sessions) < items_per_page:
                    break

        except Exception as exc:
            logging.error("Failed to fetch AudiobookShelf sessions: %s", exc)
            if job_id is not None:
                self._update_job(
                    job_id,
                    status=HistoricalImportJob.STATUS_FAILED,
                    error_message=str(exc),
                )
            return {
                "success": False,
                "error": str(exc),
                "total_fetched": 0,
                "total_processed": 0,
                "total_stored": 0,
            }

        # Store imported sessions
        stored_count = self._store_activity_sessions(imported_sessions, job_id=job_id)

        if job_id is not None:
            expected_total = (
                total_sessions if total_sessions is not None else entries_seen
            )
            self._update_job(
                job_id,
                total_fetched=expected_total,
                total_processed=len(imported_sessions),
                total_stored=stored_count,
            )

        logging.info(
            "AudiobookShelf historical import complete: %s sessions inspected, %s sessions stored",
            entries_seen,
            stored_count,
        )

        return {
            "success": True,
            "total_fetched": entries_seen,
            "total_processed": len(imported_sessions),
            "total_stored": stored_count,
            "date_range": {
                "from": cutoff.isoformat(),
                "to": datetime.now(UTC).isoformat(),
            },
        }

    @staticmethod
    def _ticks_to_ms(value) -> int:
        try:
            if value is None:
                return 0
            if isinstance(value, str):
                value = int(value)
            if isinstance(value, (int, float)):
                return max(int(value / 10000), 0)
        except (ValueError, TypeError):
            return 0
        return 0

    @staticmethod
    def _ticks_to_datetime(value) -> datetime | None:
        try:
            if value is None:
                return None
            if isinstance(value, str):
                value = int(value)
            if not isinstance(value, (int, float)):
                return None
            ticks = int(value)
            epoch_offset = 621355968000000000  # ticks between 0001-01-01 and 1970-01-01
            seconds = (ticks - epoch_offset) / 10_000_000
            return datetime.fromtimestamp(seconds, UTC)
        except (ValueError, TypeError, OverflowError):
            return None

    @staticmethod
    def _parse_datetime(value) -> datetime | None:
        if not value:
            return None

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)

        try:
            if isinstance(value, int):
                return datetime.fromtimestamp(value, UTC)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned.endswith("Z"):
                    cleaned = cleaned[:-1] + "+00:00"
                try:
                    dt = datetime.fromisoformat(cleaned)
                except ValueError:
                    # Normalise fractional seconds to microsecond precision
                    tz_suffix = ""
                    for sign in ("+", "-"):
                        idx = cleaned.find(sign, 1)
                        if idx != -1:
                            tz_suffix = cleaned[idx:]
                            cleaned = cleaned[:idx]
                            break

                    if "." in cleaned:
                        main, frac = cleaned.split(".", 1)
                        frac = "".join(ch for ch in frac if ch.isdigit())[:6]
                        cleaned = main + (f".{frac}" if frac else "")
                    cleaned = cleaned + tz_suffix
                    dt = datetime.fromisoformat(cleaned)

                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt.astimezone(UTC)
        except Exception:
            return None

        return None

    def _build_activity_session(
        self,
        *,
        session_id: str,
        user_name: str,
        user_id: str,
        media_title: str,
        media_type: str,
        media_id: str,
        series_name: str | None,
        season_number: int | None,
        episode_number: int | None,
        started_at: datetime,
        duration_ms: int,
        viewed_at: datetime,
        metadata: dict[str, Any] | None = None,
    ):
        from app.models import ActivitySession

        try:
            session = ActivitySession(
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

            combined_metadata = {
                k: v for k, v in (metadata or {}).items() if v is not None
            }
            combined_metadata.setdefault("status", "ended")
            combined_metadata.setdefault(
                "imported_from", f"{self.media_server.server_type}_history"
            )
            combined_metadata.setdefault(
                "import_timestamp", datetime.now(UTC).isoformat()
            )
            combined_metadata.setdefault("historical_viewed_at", viewed_at.isoformat())
            session.set_metadata(combined_metadata)

            if apply_identity_resolution:
                try:
                    apply_identity_resolution(session)
                except Exception as exc:  # pragma: no cover - advisory
                    logging.debug(
                        "Identity resolution failed for historical session %s: %s",
                        session.session_id,
                        exc,
                    )

            return session
        except Exception as exc:
            logging.warning("Failed to build historical activity session: %s", exc)
            return None

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
            from app.models import ActivitySession

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

            if isinstance(user_name, str):
                user_name = user_name.strip()
            user_name = user_name or "Unknown User"

            # Extract media data with safe fallbacks
            raw_title = getattr(entry, "title", None)
            if isinstance(raw_title, str):
                raw_title = raw_title.strip()
            media_title = raw_title or "Unknown Media"
            media_type = getattr(entry, "type", "unknown").lower()
            media_id = str(getattr(entry, "ratingKey", ""))

            # Handle episodes - extract series info
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

                # Keep original episode title for media_title
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

    def _store_activity_sessions(
        self, sessions: list, job_id: int | None = None
    ) -> int:
        """Store activity sessions in the database."""
        from app.models import ActivitySession

        stored_count = 0

        for session in sessions:
            try:
                # Check if session already exists to avoid duplicates
                existing = (
                    ActivitySession.query.filter_by(
                        session_id=session.session_id, server_id=session.server_id
                    )
                    .with_entities(ActivitySession.id)
                    .first()
                )

                if existing:
                    continue

                db.session.add(session)
                db.session.commit()
                stored_count += 1

                if job_id is not None and stored_count % 25 == 0:
                    self._update_job(job_id, total_stored=stored_count)

            except Exception as exc:
                logging.warning(
                    "Failed to store activity session %s (server %s): %s",
                    getattr(session, "session_id", "unknown"),
                    getattr(session, "server_id", "unknown"),
                    exc,
                    exc_info=True,
                )
                db.session.rollback()
                if job_id is not None:
                    self._update_job(job_id, error_message=str(exc))

        if job_id is not None:
            self._update_job(job_id, total_stored=stored_count)

        return stored_count

    @staticmethod
    def _update_job(job_id: int, **fields) -> None:
        """Persist updates to a historical import job."""
        job = HistoricalImportJob.query.get(job_id)
        if not job:
            return

        for key, value in fields.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(UTC)
        db.session.commit()

    @staticmethod
    def _run_import_job(
        app,
        job_id: int,
        server_id: int,
        days_back: int,
        max_results: int | None,
    ) -> None:
        """Background worker wrapper for historical imports."""
        with app.app_context():
            job = HistoricalImportJob.query.get(job_id)
            if not job:
                logging.error("Historical import job %s not found", job_id)
                return

            job.status = HistoricalImportJob.STATUS_RUNNING
            job.started_at = datetime.now(UTC)
            job.error_message = None
            job.total_fetched = 0
            job.total_processed = 0
            job.total_stored = 0
            job.updated_at = datetime.now(UTC)
            db.session.commit()

            service = HistoricalDataService(server_id)

            try:
                result = service.import_history(
                    days_back=days_back,
                    max_results=max_results,
                    job_id=job_id,
                )
                job = HistoricalImportJob.query.get(job_id)
                if not job:
                    return
                if result.get("success"):
                    job.status = HistoricalImportJob.STATUS_COMPLETED
                else:
                    job.status = HistoricalImportJob.STATUS_FAILED
                    job.error_message = result.get("error")
                job.total_fetched = result.get("total_fetched", job.total_fetched)
                job.total_processed = result.get("total_processed", job.total_processed)
                job.total_stored = result.get("total_stored", job.total_stored)
                job.updated_at = datetime.now(UTC)
                db.session.commit()
            except Exception as exc:
                logging.error("Historical import job %s failed: %s", job_id, exc)
                db.session.rollback()
                job = HistoricalImportJob.query.get(job_id)
                if job:
                    job.status = HistoricalImportJob.STATUS_FAILED
                    job.error_message = str(exc)
                    job.updated_at = datetime.now(UTC)
                    db.session.commit()
            finally:
                job = HistoricalImportJob.query.get(job_id)
                if job:
                    job.finished_at = datetime.now(UTC)
                    job.updated_at = datetime.now(UTC)
                    db.session.commit()

            # Clean up completed jobs so we don't persist history indefinitely
            job = HistoricalImportJob.query.get(job_id)
            if job and job.status == HistoricalImportJob.STATUS_COMPLETED:
                db.session.delete(job)
                db.session.commit()

    def get_import_statistics(self) -> dict[str, Any]:
        """Get statistics about imported historical data."""
        try:
            from app.models import ActivitySession

            # Get basic counts for imported historical data (any source)
            imported_query = ActivitySession.query.filter(
                ActivitySession.server_id == self.server_id,
                db.or_(
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "plex_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "jellyfin_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "emby_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "audiobookshelf_history"%'
                    ),
                ),
            )

            total_entries = imported_query.count()
            unique_users = (
                db.session.query(ActivitySession.user_id)
                .filter(
                    ActivitySession.server_id == self.server_id,
                    db.or_(
                        ActivitySession.session_metadata.like(
                            '%"imported_from": "plex_history"%'
                        ),
                        ActivitySession.session_metadata.like(
                            '%"imported_from": "jellyfin_history"%'
                        ),
                        ActivitySession.session_metadata.like(
                            '%"imported_from": "emby_history"%'
                        ),
                        ActivitySession.session_metadata.like(
                            '%"imported_from": "audiobookshelf_history"%'
                        ),
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
            from app.models import ActivitySession

            # Delete only imported historical data, not live activity data
            # Match any historical import source (plex, jellyfin, emby, audiobookshelf)
            deleted_count = ActivitySession.query.filter(
                ActivitySession.server_id == self.server_id,
                db.or_(
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "plex_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "jellyfin_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "emby_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "audiobookshelf_history"%'
                    ),
                ),
            ).count()

            ActivitySession.query.filter(
                ActivitySession.server_id == self.server_id,
                db.or_(
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "plex_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "jellyfin_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "emby_history"%'
                    ),
                    ActivitySession.session_metadata.like(
                        '%"imported_from": "audiobookshelf_history"%'
                    ),
                ),
            ).delete(synchronize_session=False)

            db.session.commit()

            return {"success": True, "deleted_count": deleted_count}

        except Exception as e:
            logging.error(f"Failed to clear historical data: {e}")
            db.session.rollback()
            return {"success": False, "error": str(e), "deleted_count": 0}
