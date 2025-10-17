"""
Ingestion service for Wizarr activity events.

Responsible for translating media server events into database records while
keeping session grouping and identity resolution concerns encapsulated.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

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

        db.session.commit()  # type: ignore[union-attr]
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

        if event.user_name and event.user_name.lower() not in {
            "unknown",
            "unknown user",
        }:
            session.user_name = event.user_name
        if event.user_id:
            session.user_id = event.user_id

        updated_session = self._update_session_from_event(session, event)

        if event.position_ms is not None and event.state:
            self._create_snapshot(session.id, event)

        self._assign_session_identity(updated_session)
        db.session.commit()  # type: ignore[union-attr]
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
        db.session.commit()  # type: ignore[union-attr]

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
        try:
            previous_sessions = (
                db.session.query(ActivitySession)  # type: ignore[union-attr]
                .filter_by(
                    server_id=event.server_id,
                    user_name=event.user_name,
                    media_id=event.media_id,
                )
                .filter(ActivitySession.id < new_session.id)
                .order_by(ActivitySession.id.desc())
                .limit(2)
                .all()
            )

            if not previous_sessions:
                new_session.reference_id = new_session.id
                return

            prev_session = previous_sessions[0]

            prev_timestamp = prev_session.updated_at or prev_session.started_at
            event_timestamp = event.timestamp

            if prev_timestamp.tzinfo is None and event_timestamp.tzinfo is not None:  # type: ignore[union-attr]
                prev_timestamp = prev_timestamp.replace(tzinfo=UTC)
            elif (
                prev_timestamp.tzinfo is not None and event_timestamp.tzinfo is not None
            ):  # type: ignore[union-attr]
                event_timestamp = event_timestamp.replace(tzinfo=UTC)  # type: ignore[union-attr]

            time_gap = event_timestamp - prev_timestamp
            should_group = time_gap.total_seconds() < 1800

            if should_group:
                if prev_session.reference_id is None:
                    prev_session.reference_id = prev_session.id
                new_session.reference_id = prev_session.reference_id
            else:
                new_session.reference_id = new_session.id

        except Exception as exc:
            new_session.reference_id = new_session.id
            self.logger.warning(
                "Session grouping failed for %s: %s", event.session_id, exc
            )

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
