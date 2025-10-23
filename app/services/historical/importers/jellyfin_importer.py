"""Jellyfin and Emby historical data importer."""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from app.services.historical.utils import (
    build_activity_session,
    parse_datetime,
    ticks_to_datetime,
    ticks_to_ms,
)

logger = structlog.get_logger(__name__)


class JellyfinHistoricalImporter:
    """Handles importing historical playback data from Jellyfin/Emby servers."""

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
        """Import historical playback data from Jellyfin/Emby."""
        from app.services.media import get_media_client

        client = get_media_client(
            self.media_server.server_type, media_server=self.media_server
        )

        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        logger.info(
            "jellyfin_import_started",
            server_type=self.media_server.server_type.title(),
            days_back=days_back,
            max_results=max_results or "unlimited",
        )

        try:
            users_response = client.get("/Users").json()
        except Exception as exc:
            logger.error("users_fetch_failed", error=str(exc))
            return {
                "success": False,
                "error": str(exc),
                "sessions": [],
                "total_fetched": 0,
                "total_processed": 0,
            }

        imported_sessions: list = []
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
                    logger.warning(
                        "user_history_fetch_failed",
                        user_id=user_id,
                        error=str(exc),
                    )
                    break

                items = response.get("Items", [])
                if not items:
                    break

                logger.debug(
                    "page_fetched",
                    server_type=self.media_server.server_type,
                    user_name=user_name,
                    items_count=len(items),
                    start_index=start_index,
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
                    if update_job_callback:
                        update_job_callback(
                            job_id,
                            total_fetched=expected_total,
                            total_processed=len(imported_sessions),
                        )

                for item in items:
                    if maybe_stop():
                        break

                    session = self._process_item(
                        item, user_name, user_id, cutoff, exhausted
                    )
                    if session is None:
                        continue

                    if session == "exhausted":
                        exhausted = True
                        continue

                    imported_sessions.append(session)
                    total_seen += 1

                    if (
                        job_id is not None
                        and total_seen % 25 == 0
                        and update_job_callback
                    ):
                        update_job_callback(
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
                logger.debug(
                    "user_import_complete",
                    server_type=self.media_server.server_type,
                    user_name=user_name,
                    sessions_count=len(imported_sessions) - user_sessions_before,
                )

        logger.info(
            "jellyfin_import_complete",
            server_type=self.media_server.server_type.title(),
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

    def _process_item(
        self,
        item: dict,
        user_name: str,
        user_id: str,
        cutoff: datetime,
        _exhausted: bool,
    ) -> Any:
        """Process a single Jellyfin/Emby item into ActivitySession."""
        user_data = item.get("UserData") or {}
        last_played_raw = user_data.get("LastPlayedDate")
        viewed_at = parse_datetime(last_played_raw)
        if viewed_at is None:
            viewed_at = ticks_to_datetime(user_data.get("LastPlayedDateTicks"))
        if not viewed_at:
            return None

        if viewed_at < cutoff:
            return "exhausted"

        duration_ms = ticks_to_ms(item.get("RunTimeTicks"))
        position_ms = ticks_to_ms(user_data.get("PlaybackPositionTicks"))

        started_at = viewed_at
        if duration_ms and duration_ms > 0:
            started_at = viewed_at - timedelta(milliseconds=duration_ms)
        elif position_ms and position_ms > 0:
            started_at = viewed_at - timedelta(milliseconds=position_ms)

        media_type = (item.get("Type") or "unknown").lower()
        media_title = (item.get("Name") or "Unknown Media").strip() or "Unknown Media"
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
            "historical_duration_source": "runtime_ticks" if duration_ms else None,
            "historical_user_id": str(user_id),
        }

        return build_activity_session(
            server_id=self.server_id,
            server_type=self.media_server.server_type,
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
