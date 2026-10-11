"""
Shared utilities for historical data import.

Provides datetime parsing, tick conversion, and session building helpers.
"""

from datetime import UTC, datetime
from typing import Any

import structlog

from app.models import ActivitySession

logger = structlog.get_logger(__name__)


def ticks_to_ms(value) -> int:
    """Convert .NET ticks to milliseconds."""
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


def ticks_to_datetime(value) -> datetime | None:
    """Convert .NET ticks to datetime."""
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


def parse_datetime(value) -> datetime | None:
    """Parse various datetime formats to UTC datetime."""
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


def build_activity_session(
    server_id: int,
    server_type: str,
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
) -> ActivitySession | None:
    """Build an ActivitySession from historical data."""
    try:
        session = ActivitySession(
            server_id=server_id,
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

        combined_metadata = {k: v for k, v in (metadata or {}).items() if v is not None}
        combined_metadata.setdefault("status", "ended")
        combined_metadata.setdefault("imported_from", f"{server_type}_history")
        combined_metadata.setdefault("import_timestamp", datetime.now(UTC).isoformat())
        combined_metadata.setdefault("historical_viewed_at", viewed_at.isoformat())
        session.set_metadata(combined_metadata)

        try:
            from app.services.activity.identity_resolution import (
                apply_identity_resolution,
            )

            if apply_identity_resolution:
                apply_identity_resolution(session)
        except Exception as exc:  # pragma: no cover
            logger.debug(
                "identity_resolution_failed",
                session_id=session.session_id,
                error=str(exc),
            )

        return session
    except Exception as exc:
        logger.warning("session_build_failed", error=str(exc))
        return None
