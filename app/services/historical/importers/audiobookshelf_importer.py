"""AudiobookShelf historical data importer."""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.services.historical.utils import build_activity_session

logger = structlog.get_logger(__name__)


class AudiobookShelfHistoricalImporter:
    """Handles importing historical listening session data from AudiobookShelf servers."""

    def __init__(self, server_id: int, media_server):
        self.server_id = server_id
        self.media_server = media_server

    def import_history(
        self,
        days_back: int,
        max_results: int | None,
        job_id: int | None,
        update_job_callback=None,
    ) -> dict[str, Any]:
        """Import historical listening session data from AudiobookShelf."""
        from app.services.media import get_media_client

        client = get_media_client(
            self.media_server.server_type, media_server=self.media_server
        )

        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        logger.info(
            "abs_import_started",
            days_back=days_back,
            max_results=max_results or "unlimited",
        )

        endpoint = f"{client.API_PREFIX}/sessions"
        imported_sessions: list = []
        total_seen = 0
        entries_seen = 0
        page = 0
        items_per_page = 100
        total_sessions: int | None = None

        def maybe_stop() -> bool:
            return max_results is not None and total_seen >= max_results

        try:
            while not maybe_stop():
                query_params = {"itemsPerPage": str(items_per_page), "page": str(page)}

                try:
                    response = client.get(endpoint, params=query_params)
                    response.raise_for_status()
                    data = response.json()
                except Exception as exc:
                    logger.warning(
                        "page_fetch_failed",
                        page=page,
                        error=str(exc),
                    )
                    break

                sessions = data.get("sessions", [])
                if not sessions:
                    break

                total_sessions = data.get("total", total_sessions)
                entries_seen += len(sessions)

                logger.debug(
                    "page_fetched",
                    sessions_count=len(sessions),
                    page=page,
                )

                if job_id is not None and entries_seen % 100 == 0:
                    expected_total = (
                        total_sessions if total_sessions is not None else entries_seen
                    )
                    if update_job_callback:
                        update_job_callback(
                            job_id,
                            total_fetched=expected_total,
                            total_processed=len(imported_sessions),
                        )

                exhausted = False
                for session in sessions:
                    if maybe_stop() or exhausted:
                        break

                    result = self._process_session(session, cutoff)
                    if result is None:
                        continue
                    if result == "exhausted":
                        exhausted = True
                        continue

                    imported_sessions.append(result)
                    total_seen += 1

                    if (
                        job_id is not None
                        and total_seen % 25 == 0
                        and update_job_callback
                    ):
                        update_job_callback(
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

                page += 1
                if len(sessions) < items_per_page:
                    break

        except Exception as exc:
            logger.error("abs_import_failed", error=str(exc))
            return {
                "success": False,
                "error": str(exc),
                "sessions": [],
                "total_fetched": 0,
                "total_processed": 0,
            }

        logger.info(
            "abs_import_complete",
            entries_seen=entries_seen,
            sessions_processed=len(imported_sessions),
        )

        return {
            "success": True,
            "sessions": imported_sessions,
            "total_fetched": entries_seen,
            "total_processed": len(imported_sessions),
            "date_range": {
                "from": cutoff.isoformat(),
                "to": datetime.now(UTC).isoformat(),
            },
        }

    def _process_session(self, session: dict, cutoff: datetime) -> Any:
        """Process a single AudiobookShelf session into ActivitySession."""
        if not isinstance(session, dict):
            return None

        # Get session timestamps
        updated_at_ms = session.get("updatedAt")
        started_at_ms = session.get("startedAt")

        # Parse viewed_at
        viewed_at = None
        if updated_at_ms:
            viewed_at = datetime.fromtimestamp(updated_at_ms / 1000, UTC)

        if not viewed_at:
            return None

        # Check date range
        if viewed_at < cutoff:
            return "exhausted"

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
        media_id = str(session.get("libraryItemId") or session.get("id", ""))
        session_id_raw = str(session.get("id", ""))

        # Calculate duration and position
        time_listening_s = session.get("timeListening", 0) or 0
        current_time_s = session.get("currentTime", 0) or 0

        duration_ms = int(time_listening_s * 1000) if time_listening_s else 0
        position_ms = int(current_time_s * 1000)

        # Calculate started_at
        if started_at_ms:
            started_at = datetime.fromtimestamp(started_at_ms / 1000, UTC)
        elif duration_ms and duration_ms > 0:
            started_at = viewed_at - timedelta(milliseconds=duration_ms)
        elif updated_at_ms and started_at_ms:
            session_duration_ms = updated_at_ms - started_at_ms
            started_at = viewed_at - timedelta(milliseconds=session_duration_ms)
        else:
            started_at = viewed_at

        # Generate session ID
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
            "historical_duration_source": "time_listening",
            "historical_user_id": str(user_id),
            "abs_session_id": session_id_raw,
            "play_method": session.get("playMethod"),
            "time_listening_seconds": time_listening_s,
        }

        # Add device info if available
        device_info = session.get("deviceInfo")
        if device_info:
            metadata["device_info"] = device_info

        return build_activity_session(
            server_id=self.server_id,
            server_type=self.media_server.server_type,
            session_id=session_id,
            user_name=user_name,
            user_id=user_id,
            media_title=media_title,
            media_type=media_type,
            media_id=media_id,
            series_name=None,
            season_number=None,
            episode_number=None,
            started_at=started_at,
            duration_ms=duration_ms,
            viewed_at=viewed_at,
            metadata=metadata,
        )
