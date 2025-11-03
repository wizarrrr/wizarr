"""
Ingestion service for Wizarr activity events.

Responsible for translating media server events into database records while
keeping session grouping and identity resolution concerns encapsulated.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import structlog
from sqlalchemy.exc import OperationalError

try:
    from app.extensions import db  # type: ignore
except ImportError:  # pragma: no cover - during unit tests
    db = None  # type: ignore

from app.activity.domain.models import ActivityEvent
from app.models import ActivitySession, ActivitySnapshot
from app.services.activity.identity_resolution import apply_identity_resolution


class ActivityIngestionService:
    """Persist and update activity sessions based on incoming events."""

    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    def _commit_with_retry(self, max_retries: int = 3, base_delay: float = 0.1) -> bool:
        """
        Commit database changes with exponential backoff retry logic.

        This is critical for SQLite which only allows one writer at a time.
        Background threads competing with request handlers can cause lock timeouts.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds (doubles each retry)

        Returns:
            True if commit succeeded, False otherwise
        """
        if db is None:
            return False

        for attempt in range(max_retries):
            try:
                db.session.commit()  # type: ignore[union-attr]
                return True
            except OperationalError as exc:
                # Check if it's a database lock error
                if (
                    "database is locked" in str(exc).lower()
                    or "locked" in str(exc).lower()
                ):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        self.logger.warning(
                            "Database locked, retrying in %.2fs (attempt %d/%d)",
                            delay,
                            attempt + 1,
                            max_retries,
                        )
                        time.sleep(delay)
                        db.session.rollback()  # type: ignore[union-attr]
                        continue
                    self.logger.error(
                        "Database commit failed after %d attempts: %s",
                        max_retries,
                        exc,
                        exc_info=True,
                    )
                    db.session.rollback()  # type: ignore[union-attr]
                    return False
                # Not a lock error, re-raise
                raise
            except Exception as exc:
                self.logger.error("Unexpected commit error: %s", exc, exc_info=True)
                db.session.rollback()  # type: ignore[union-attr]
                return False

        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def record_activity_event(self, event: ActivityEvent) -> ActivitySession | None:
        """Record a new activity event and return the affected session."""
        if db is None:
            self.logger.warning("Database not available, skipping activity recording")
            return None

        try:
            handlers = {
                "session_start": self._handle_session_start,
                "session_end": self._handle_session_end,
                "session_progress": self._handle_session_update,
                "session_pause": self._handle_session_update,
                "session_resume": self._handle_session_update,
                "session_buffer": self._handle_session_update,
            }

            handler = handlers.get(event.event_type)
            if not handler:
                self.logger.warning("Unknown activity event type: %s", event.event_type)
                return None

            return handler(event)

        except Exception as exc:  # pragma: no cover - defensive rollback
            self.logger.error("Failed to record activity event: %s", exc, exc_info=True)
            db.session.rollback()  # type: ignore[union-attr]
            return None

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _handle_session_start(self, event: ActivityEvent) -> ActivitySession:
        existing_session = (
            db.session.query(ActivitySession)  # type: ignore[union-attr]
            .filter_by(server_id=event.server_id, session_id=event.session_id)
            .filter(ActivitySession.active.is_(True))
            .first()
        )

        if existing_session:
            self.logger.debug("Session %s already exists, updating", event.session_id)
            return self._update_session_from_event(existing_session, event)

        session = ActivitySession(
            server_id=event.server_id,
            session_id=event.session_id,
            user_name=event.user_name,
            user_id=event.user_id,
            media_title=event.media_title,
            media_type=event.media_type,
            media_id=event.media_id,
            series_name=event.series_name,
            season_number=event.season_number,
            episode_number=event.episode_number,
            started_at=event.timestamp,
            active=True,
            duration_ms=event.duration_ms,
            device_name=event.device_name,
            client_name=event.client_name,
            ip_address=event.ip_address,
            platform=event.platform,
            player_version=event.player_version,
            artwork_url=event.artwork_url,
            thumbnail_url=event.thumbnail_url,
        )

        if event.transcoding_info:
            session.set_transcoding_info(event.transcoding_info)
        if event.metadata:
            session.set_metadata(event.metadata)

        metadata = session.get_metadata()
        metadata["status"] = "active"
        session.set_metadata(metadata)

        self._assign_session_identity(session)

        db.session.add(session)  # type: ignore[union-attr]
        db.session.flush()  # type: ignore[union-attr]

        self._apply_session_grouping(session, event)

        if event.position_ms is not None and event.state:
            self._create_snapshot(session.id, event)

        self._commit_with_retry()
        self.logger.info(
            "Started tracking session %s for user %s",
            event.session_id,
            event.user_name,
        )
        return session

    def _handle_session_update(self, event: ActivityEvent) -> ActivitySession | None:
        session = (
            db.session.query(ActivitySession)  # type: ignore[union-attr]
            .filter_by(server_id=event.server_id, session_id=event.session_id)
            .filter(ActivitySession.active.is_(True))
            .first()
        )

        if not session:
            self.logger.debug(
                "Session %s not found for update, creating new session",
                event.session_id,
            )
            event.event_type = "session_start"
            return self._handle_session_start(event)

        # Tautulli approach: Allow enrichment by overwriting "Unknown" values
        # Update fields if: (1) current value is Unknown OR (2) new value is not Unknown
        def should_update(current_value: str | None, new_value: str | None) -> bool:
            """Check if field should be updated based on enrichment rules."""
            if not new_value:
                return False
            new_is_unknown = new_value.lower() in {"unknown", "unknown user"}
            if not current_value or current_value.lower() in {
                "unknown",
                "unknown user",
            }:
                # Current is Unknown, update if new is not Unknown
                return not new_is_unknown
            # Current has value, only update if new is also not Unknown
            return not new_is_unknown

        if should_update(session.user_name, event.user_name):
            self.logger.debug(
                "Enriching session %s user_name: %s -> %s",
                event.session_id,
                session.user_name,
                event.user_name,
            )
            session.user_name = event.user_name

        if event.user_id:
            session.user_id = event.user_id

        if should_update(session.media_title, event.media_title):
            self.logger.debug(
                "Enriching session %s media_title: %s -> %s",
                event.session_id,
                session.media_title,
                event.media_title,
            )
            session.media_title = event.media_title

        if should_update(session.device_name, event.device_name):
            self.logger.debug(
                "Enriching session %s device_name: %s -> %s",
                event.session_id,
                session.device_name,
                event.device_name,
            )
            session.device_name = event.device_name

        if should_update(session.client_name, event.client_name):
            session.client_name = event.client_name

        if should_update(session.platform, event.platform):
            session.platform = event.platform

        if event.media_type and event.media_type.lower() != "unknown":
            session.media_type = event.media_type

        if event.media_id:
            session.media_id = event.media_id

        updated_session = self._update_session_from_event(session, event)

        if event.position_ms is not None and event.state:
            self._create_snapshot(session.id, event)

        self._assign_session_identity(updated_session)
        self._commit_with_retry()
        return updated_session

    def _handle_session_end(self, event: ActivityEvent) -> ActivitySession | None:
        session = (
            db.session.query(ActivitySession)  # type: ignore[union-attr]
            .filter_by(server_id=event.server_id, session_id=event.session_id)
            .filter(ActivitySession.active.is_(True))
            .first()
        )

        if not session:
            self.logger.debug(
                "Session %s not found for end event, skipping", event.session_id
            )
            return None

        self._update_session_from_event(session, event)

        session.active = False
        metadata = session.get_metadata()
        if event.timestamp:
            metadata["last_end_timestamp"] = event.timestamp.isoformat()
        metadata["status"] = "ended"
        session.set_metadata(metadata)

        if event.position_ms is not None:
            self._create_snapshot(session.id, event)

        self._assign_session_identity(session)
        self._commit_with_retry()

        self.logger.info(
            "Closed session %s for user %s", event.session_id, event.user_name
        )
        return session

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _assign_session_identity(self, session: ActivitySession) -> bool:
        try:
            return bool(apply_identity_resolution(session))
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Identity resolution skipped: %s", exc)
            return False

    def _apply_session_grouping(
        self,
        new_session: ActivitySession,
        event: ActivityEvent,
    ) -> None:
        """
        Apply session grouping with multi-level matching strategy.

        Handles real-world scenarios where Plex creates new sessionKeys for:
        - Subtitle/audio track changes
        - Quality/transcoding changes
        - App quit/resume
        - Network reconnections

        Uses fallback matching when media_id is missing during initial creation.
        """
        try:
            # Find potential previous sessions using flexible matching
            previous_sessions = self._find_groupable_sessions(
                event.server_id,
                event.user_name,
                event.media_id,
                event.media_title,
                event.device_name,
                new_session.id,
            )

            if not previous_sessions:
                new_session.reference_id = new_session.id
                self.logger.debug(
                    "No groupable sessions found for %s, creating new group",
                    event.session_id,
                )
                return

            prev_session = previous_sessions[0]

            prev_timestamp = prev_session.updated_at or prev_session.started_at
            event_timestamp = event.timestamp

            # Normalize both timestamps to UTC properly
            if prev_timestamp.tzinfo is None:  # type: ignore[union-attr]
                prev_timestamp = prev_timestamp.replace(tzinfo=UTC)  # type: ignore[union-attr]
            else:
                prev_timestamp = prev_timestamp.astimezone(UTC)  # type: ignore[union-attr]

            if event_timestamp.tzinfo is None:  # type: ignore[union-attr]
                event_timestamp = event_timestamp.replace(tzinfo=UTC)  # type: ignore[union-attr]
            else:
                event_timestamp = event_timestamp.astimezone(UTC)  # type: ignore[union-attr]

            time_gap = event_timestamp - prev_timestamp
            gap_seconds = time_gap.total_seconds()

            # Extended window: 2 hours (handles dinner breaks, phone calls, etc.)
            # Previous 30-minute window was too strict for real-world usage
            time_window_seconds = 7200  # 2 hours

            should_group = gap_seconds < time_window_seconds

            if should_group:
                if prev_session.reference_id is None:
                    prev_session.reference_id = prev_session.id
                new_session.reference_id = prev_session.reference_id

                self.logger.info(
                    "Grouped session %s with reference %s (gap: %.0fs, media_id: %s)",
                    event.session_id,
                    prev_session.reference_id,
                    gap_seconds,
                    event.media_id or "unknown",
                )
            else:
                new_session.reference_id = new_session.id
                self.logger.debug(
                    "Session %s not grouped - gap %.0fs exceeds window",
                    event.session_id,
                    gap_seconds,
                )

        except Exception as exc:
            new_session.reference_id = new_session.id
            self.logger.warning(
                "Session grouping failed for %s: %s", event.session_id, exc
            )

    def _find_groupable_sessions(
        self,
        server_id: int,
        user_name: str,
        media_id: str | None,
        media_title: str,
        device_name: str | None,
        current_session_id: int,
    ) -> list[ActivitySession]:
        """
        Find previous sessions that should be grouped using multi-level matching.

        Priority order:
        1. Exact media_id match (highest confidence)
        2. Title + Device match (medium confidence - handles subtitle changes)
        3. Title-only match (lower confidence - handles device changes)

        Returns:
            List of up to 2 most recent matching sessions
        """
        base_query = db.session.query(ActivitySession).filter(  # type: ignore[union-attr]
            ActivitySession.server_id == server_id,
            ActivitySession.user_name == user_name,
            ActivitySession.id < current_session_id,
        )

        # Strategy 1: Exact media_id match (if available and not "Unknown")
        # Defensive: Convert media_id to string since it may come as int from some sources
        if media_id:
            media_id_str = str(media_id) if not isinstance(media_id, str) else media_id
            if media_id_str.lower() != "unknown":
                exact_matches = (
                    base_query.filter(ActivitySession.media_id == media_id_str)
                    .order_by(ActivitySession.id.desc())
                    .limit(2)
                    .all()
                )
                if exact_matches:
                    self.logger.debug(
                        "Found %d sessions via media_id match (%s)",
                        len(exact_matches),
                        media_id_str,
                    )
                    return exact_matches

        # Strategy 2: Title + Device match
        # Handles cases where:
        # - media_id is missing/unknown during initial session creation
        # - User changed subtitle/audio (new sessionKey but same viewing session)
        # Defensive: Convert device_name to string since it may come as int from some sources
        if device_name:
            device_name_str = (
                str(device_name) if not isinstance(device_name, str) else device_name
            )
            if device_name_str.lower() != "unknown":
                title_device_matches = (
                    base_query.filter(
                        ActivitySession.media_title == media_title,
                        ActivitySession.device_name == device_name_str,
                    )
                    .order_by(ActivitySession.id.desc())
                    .limit(2)
                    .all()
                )
                if title_device_matches:
                    self.logger.debug(
                        "Found %d sessions via title+device match (%s on %s)",
                        len(title_device_matches),
                        media_title,
                        device_name_str,
                    )
                    return title_device_matches

        # Strategy 3: Title-only match (last resort)
        # Handles cases where device info is also missing
        title_matches = (
            base_query.filter(ActivitySession.media_title == media_title)
            .order_by(ActivitySession.id.desc())
            .limit(2)
            .all()
        )
        if title_matches:
            self.logger.debug(
                "Found %d sessions via title-only match (%s)",
                len(title_matches),
                media_title,
            )
        return title_matches

    def _update_session_from_event(
        self,
        session: ActivitySession,
        event: ActivityEvent,
    ) -> ActivitySession:
        metadata = session.get_metadata()
        if event.position_ms is not None:
            metadata["last_known_position_ms"] = event.position_ms
        if event.metadata:
            metadata.update(event.metadata)

        total_duration_seconds = metadata.get("total_duration_seconds")

        if event.duration_ms is not None:
            session.duration_ms = event.duration_ms
        elif total_duration_seconds is not None:
            try:
                session.duration_ms = max(int(float(total_duration_seconds) * 1000), 0)
            except (TypeError, ValueError):
                self.logger.debug(
                    "Invalid total_duration_seconds value: %s", total_duration_seconds
                )

        if event.transcoding_info:
            session.set_transcoding_info(event.transcoding_info)

        session.set_metadata(metadata if metadata else {})

        session.updated_at = datetime.now(UTC)
        self._assign_session_identity(session)
        return session

    def _create_snapshot(self, session_id: int, event: ActivityEvent) -> None:
        snapshot = ActivitySnapshot(
            session_id=session_id,
            timestamp=event.timestamp,
            position_ms=event.position_ms,
            state=event.state or "unknown",
            bandwidth_kbps=event.bandwidth_kbps,
            quality=event.quality,
            subtitle_stream=event.subtitle_stream,
            audio_stream=event.audio_stream,
        )

        if event.transcoding_info:
            snapshot.set_transcoding_details(event.transcoding_info)

        db.session.add(snapshot)  # type: ignore[union-attr]


__all__ = ["ActivityIngestionService"]
