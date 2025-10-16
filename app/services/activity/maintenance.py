"""
Maintenance tasks for Wizarr activity data.

These helpers support scheduled jobs that clean up or reconcile sessions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

try:
    from app.extensions import db  # type: ignore
except ImportError:  # pragma: no cover - during tests
    db = None  # type: ignore

from app.models import ActivitySession


class ActivityMaintenanceService:
    """Lifecycle management for session data."""

    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    def cleanup_old_activity(self, retention_days: int = 90) -> int:
        """Delete activity sessions older than the retention window."""
        if db is None:
            return 0

        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
            deleted_count = (
                db.session.query(ActivitySession)  # type: ignore[union-attr]
                .filter(ActivitySession.started_at < cutoff_date)
                .delete()
            )

            db.session.commit()  # type: ignore[union-attr]
            self.logger.info("Cleaned up %s old activity sessions", deleted_count)
            return deleted_count

        except Exception as exc:  # pragma: no cover - log and rollback
            self.logger.error("Failed to cleanup old activity: %s", exc, exc_info=True)
            db.session.rollback()  # type: ignore[union-attr]
            return 0

    def end_stale_sessions(self, timeout_hours: int = 24) -> int:
        """Mark sessions as ended when they have not updated within timeout."""
        if db is None:
            return 0

        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=timeout_hours)

            stale_sessions = (
                db.session.query(ActivitySession)  # type: ignore[union-attr]
                .filter(
                    ActivitySession.active.is_(True),
                    ActivitySession.updated_at < cutoff_time,
                )
                .all()
            )

            ended_count = 0
            for session in stale_sessions:
                session.active = False
                metadata = session.get_metadata()
                metadata["status"] = "ended"
                metadata["stale_closed_at"] = datetime.now(UTC).isoformat()
                session.set_metadata(metadata)
                self._end_session_gracefully(session)
                ended_count += 1

            if ended_count:
                db.session.commit()  # type: ignore[union-attr]

            self.logger.info("Ended %s stale activity sessions", ended_count)
            return ended_count

        except Exception as exc:  # pragma: no cover - log and rollback
            self.logger.error("Failed to end stale sessions: %s", exc, exc_info=True)
            db.session.rollback()  # type: ignore[union-attr]
            return 0

    def recover_sessions_on_startup(self) -> int:
        """Validate sessions when the application boots and fix stale entries."""
        if db is None:
            return 0

        try:
            active_sessions = (
                db.session.query(ActivitySession)  # type: ignore[union-attr]
                .filter(ActivitySession.active.is_(True))
                .all()
            )

            if not active_sessions:
                return 0

            self.logger.info(
                "Validating %s active sessions during startup", len(active_sessions)
            )

            sessions_by_server: dict[int, list[ActivitySession]] = {}
            for session in active_sessions:
                sessions_by_server.setdefault(session.server_id, []).append(session)

            ended_count = 0
            recovered_count = 0

            for server_id, sessions in sessions_by_server.items():
                try:
                    result = self._validate_server_sessions(server_id, sessions)
                    ended_count += result["ended"]
                    recovered_count += result["recovered"]
                except Exception as exc:
                    self.logger.warning(
                        "Failed to validate sessions for server %s: %s",
                        server_id,
                        exc,
                    )
                    for session in sessions:
                        self._end_session_gracefully(session)
                        ended_count += 1

            if ended_count or recovered_count:
                db.session.commit()  # type: ignore[union-attr]
                self.logger.info(
                    "Session recovery completed: %s recovered, %s ended",
                    recovered_count,
                    ended_count,
                )

            return ended_count

        except Exception as exc:  # pragma: no cover
            self.logger.error("Failed to recover sessions: %s", exc, exc_info=True)
            db.session.rollback()  # type: ignore[union-attr]
            return 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _validate_server_sessions(
        self,
        server_id: int,
        sessions: list[ActivitySession],
    ) -> dict[str, int]:
        """Poll the media server to verify which sessions are still active."""
        from app.models import MediaServer
        from app.services.media.service import get_client_for_media_server

        ended_count = 0
        recovered_count = 0

        try:
            server = db.session.query(MediaServer).filter_by(id=server_id).first()  # type: ignore[union-attr]
            if not server:
                self.logger.warning(
                    "Server %s not found during validation. Ending sessions.", server_id
                )
                for session in sessions:
                    self._end_session_gracefully(session)
                    ended_count += 1
                return {"ended": ended_count, "recovered": recovered_count}

            client = get_client_for_media_server(server)
            if not client:
                self.logger.warning(
                    "No client for server %s. Ending active sessions.", server_id
                )
                for session in sessions:
                    self._end_session_gracefully(session)
                    ended_count += 1
                return {"ended": ended_count, "recovered": recovered_count}

            try:
                current_sessions = client.now_playing()
            except Exception as exc:
                self.logger.warning(
                    "Failed to poll server %s sessions: %s", server_id, exc
                )
                cutoff_time = datetime.now(UTC) - timedelta(hours=1)
                for session in sessions:
                    updated_at = session.updated_at
                    if updated_at.tzinfo is None:  # type: ignore[union-attr]
                        updated_at = updated_at.replace(tzinfo=UTC)  # type: ignore[union-attr]
                    if updated_at < cutoff_time:
                        self._end_session_gracefully(session)
                        ended_count += 1
                    else:
                        recovered_count += 1
                return {"ended": ended_count, "recovered": recovered_count}

            active_session_ids = set()
            if current_sessions:
                for current_session in current_sessions:
                    session_id = self._extract_session_id(current_session)
                    if session_id:
                        active_session_ids.add(session_id)

            for session in sessions:
                if session.session_id in active_session_ids:
                    recovered_count += 1
                else:
                    self._end_session_gracefully(session)
                    ended_count += 1

        except Exception as exc:
            self.logger.error(
                "Error validating sessions for server %s: %s", server_id, exc
            )
            cutoff_time = datetime.now(UTC) - timedelta(hours=1)
            for session in sessions:
                updated_at = session.updated_at
                if updated_at.tzinfo is None:  # type: ignore[union-attr]
                    updated_at = updated_at.replace(tzinfo=UTC)  # type: ignore[union-attr]
                if updated_at < cutoff_time:
                    self._end_session_gracefully(session)
                    ended_count += 1
                else:
                    recovered_count += 1

        return {"ended": ended_count, "recovered": recovered_count}

    def _extract_session_id(self, current_session: dict) -> str | None:
        """Return the session identifier from a now_playing payload."""
        possible_fields = ["sessionKey", "session_id", "id", "key", "playSessionId"]
        for field in possible_fields:
            value = current_session.get(field)
            if value:
                return str(value)
        return None

    def _end_session_gracefully(self, session: ActivitySession) -> None:
        """Mark a session inactive while estimating its final metadata."""
        estimated_end_time = session.updated_at or session.started_at

        session.active = False
        metadata = session.get_metadata()
        metadata["graceful_closed_at"] = (
            estimated_end_time.isoformat() if estimated_end_time else None
        )
        metadata["status"] = "ended"
        session.set_metadata(metadata)

        self.logger.debug(
            "Gracefully ended session %s",
            session.session_id,
        )


__all__ = ["ActivityMaintenanceService"]
