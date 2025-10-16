"""
Activity monitoring models for Wizarr.

Tracks media playback sessions and real-time snapshots for comprehensive
activity monitoring and historical analysis.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class ActivityEvent:
    """Data transfer object for activity events before persistence."""

    event_type: str  # session_start, session_end, session_progress, session_pause, session_resume
    server_id: int
    session_id: str
    user_name: str
    media_title: str
    timestamp: datetime | None = None
    user_id: str | None = None
    media_type: str | None = None
    media_id: str | None = None
    series_name: str | None = None
    season_number: int | None = None
    episode_number: int | None = None
    duration_ms: int | None = None
    position_ms: int | None = None
    device_name: str | None = None
    client_name: str | None = None
    ip_address: str | None = None
    platform: str | None = None
    player_version: str | None = None
    state: str | None = None  # playing, paused, stopped
    transcoding_info: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    artwork_url: str | None = None
    thumbnail_url: str | None = None
    bandwidth_kbps: int | None = None
    quality: str | None = None
    subtitle_stream: str | None = None
    audio_stream: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


@dataclass
class ActivityQuery:
    """Data transfer object for activity queries."""

    server_ids: list[int] | None = None
    user_names: list[str] | None = None
    media_types: list[str] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    active_only: bool = False
    include_snapshots: bool = False
    limit: int | None = None
    offset: int | None = None
    order_by: str = "started_at"
    order_direction: str = "desc"
