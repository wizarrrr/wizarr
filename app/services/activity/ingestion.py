"""
Ingestion service for Wizarr activity events.

Responsible for translating media server events into database records while
keeping session grouping and identity resolution concerns encapsulated.

The collectors poll every 10-30 seconds and send an event for each session on
each poll. Most of these events do not change anything. The service writes a
session row only when something meaningful changes, and writes the playback
position at most once per ``POSITION_PERSIST_INTERVAL``. It writes a snapshot
only when the playback state changes.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import lazyload

try:
    from app.extensions import db  # type: ignore
except ImportError:  # pragma: no cover - during unit tests
    db = None  # type: ignore

from app.activity.domain.models import ActivityEvent
from app.models import ActivitySession, ActivitySnapshot
from app.services.activity.identity_resolution import (
    apply_identity_resolution,
    clear_identity_cache,
    resolve_user_identity_cached,
)

# Write the playback position at most once per this interval, unless the
# state changes or the session ends.
POSITION_PERSIST_INTERVAL = timedelta(seconds=60)

# Write a session that does not change (for example a paused session) at least
# once per this interval. The stale-session job and the startup recovery use
# updated_at to find sessions that are not alive.
KEEPALIVE_INTERVAL = timedelta(minutes=30)

# Metadata key that keeps the last playback state (playing, paused, ...).
PLAYBACK_STATE_KEY = "playback_state"

# Values that change on each poll. A change in only these values is not a
# meaningful change.
VOLATILE_METADATA_KEYS = frozenset({"last_known_position_ms", "session_elapsed_ms"})
VOLATILE_TRANSCODING_KEYS = frozenset({"transcoding_speed"})

_UNKNOWN_VALUES = frozenset({"unknown", "unknown user"})
_MAX_REMEMBERED_SESSIONS = 5000


def _is_known(value: Any) -> bool:
    """Return True when a value is set and is not an "Unknown" placeholder."""
    if not value:
        return False
    return str(value).lower() not in _UNKNOWN_VALUES


def _without(values: dict[str, Any], keys: frozenset[str]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if key not in keys}


def _as_stored(values: dict[str, Any]) -> dict[str, Any]:
    """Return the value as the JSON columns store it (tuples become lists, ...).

    The stored value went through the same conversion, so the comparison does
    not see a change where there is none.
    """
    return json.loads(json.dumps(values, default=str))


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_lock_error(exc: Exception) -> bool:
    return "locked" in str(exc).lower()


class _EventBatch:
    """Active sessions that one batch of events reads and changes."""

    def __init__(self):
        self.active: dict[tuple[int, str], ActivitySession] = {}
        self.wrote = False

    def load(self, events: list[ActivityEvent]) -> None:
        """Load the active sessions for all events with one query per server."""
        session_ids_by_server: dict[int, set[str]] = {}
        for event in events:
            if event.session_id:
                session_ids_by_server.setdefault(event.server_id, set()).add(
                    str(event.session_id)
                )

        for server_id, session_ids in session_ids_by_server.items():
            rows = (
                db.session.query(ActivitySession)  # type: ignore
                # The ingestion path does not use the user and identity rows.
                .options(
                    lazyload(ActivitySession.wizarr_user),
                    lazyload(ActivitySession.wizarr_identity),
                )
                .filter(
                    ActivitySession.server_id == server_id,
                    ActivitySession.session_id.in_(sorted(session_ids)),
                    ActivitySession.active.is_(True),
                )
                .order_by(ActivitySession.id.asc())
                .all()
            )
            for row in rows:
                self.active.setdefault((row.server_id, row.session_id), row)

    @staticmethod
    def key(event: ActivityEvent) -> tuple[int, str]:
        return (event.server_id, str(event.session_id))

    def find(self, event: ActivityEvent) -> ActivitySession | None:
        return self.active.get(self.key(event))


class ActivityIngestionService:
    """Persist and update activity sessions based on incoming events."""

    def __init__(self):
        self.logger = structlog.get_logger(__name__)
        # Raw media server user name that was resolved last, by session row id.
        # Identity resolution runs again only when this name changes.
        self._resolved_user_names: dict[int, str] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def record_activity_event(self, event: ActivityEvent) -> ActivitySession | None:
        """Record a new activity event and return the affected session."""
        results = self.record_activity_events([event])
        return results[0] if results else None

    def record_activity_events(
        self, events: Iterable[ActivityEvent]
    ) -> list[ActivitySession | None]:
        """
        Record the events of one poll cycle in one transaction.

        The service commits only when an event changed the database. When an
        event fails, the service rolls back and records each event alone, so
        that one bad event does not drop the other events.
        """
        events = list(events)
        if db is None:
            self.logger.warning("Database not available, skipping activity recording")
            return [None] * len(events)
        if not events:
            return []

        try:
            return self._record_batch(events)
        except Exception as exc:  # pragma: no cover - defensive rollback
            self.logger.error(
                "Failed to record activity events: %s", exc, exc_info=True
            )
            self._rollback()

        if len(events) == 1:
            return [None]

        results: list[ActivitySession | None] = []
        for event in events:
            try:
                results.extend(self._record_batch([event]))
            except Exception as exc:  # pragma: no cover - defensive rollback
                self.logger.error(
                    "Failed to record activity event: %s", exc, exc_info=True
                )
                self._rollback()
                results.append(None)
        return results

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------
    def _record_batch(
        self,
        events: list[ActivityEvent],
        max_retries: int = 3,
        base_delay: float = 0.1,
    ) -> list[ActivitySession | None]:
        """
        Apply the events and commit once.

        SQLite allows one writer at a time. When the database is locked, the
        service rolls back and applies the events again, because a rollback
        discards the pending changes.

        An integrity error can come from a cached user id of a deleted user.
        Then the service clears the identity cache and applies the events
        again one time.
        """
        attempt = 0
        identity_retry_done = False
        while True:
            batch = _EventBatch()
            try:
                # Identity resolution can query the database. Do not let that
                # query flush changes that are not complete.
                with db.session.no_autoflush:  # type: ignore
                    batch.load(events)
                    results = [self._dispatch(event, batch) for event in events]

                if batch.wrote or self._session_has_changes():
                    db.session.commit()  # type: ignore
                return results
            except IntegrityError:
                self._rollback()
                if identity_retry_done:
                    raise
                identity_retry_done = True
                self.logger.warning(
                    "Integrity error, clearing the identity cache and retrying"
                )
                clear_identity_cache()
            except OperationalError as exc:
                self._rollback()
                attempt += 1
                if _is_lock_error(exc) and attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    self.logger.warning(
                        "Database locked, retrying in %.2fs (attempt %d/%d)",
                        delay,
                        attempt,
                        max_retries,
                    )
                    time.sleep(delay)
                    continue
                raise

    def _dispatch(
        self, event: ActivityEvent, batch: _EventBatch
    ) -> ActivitySession | None:
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
        return handler(event, batch)

    def _rollback(self) -> None:
        if db is None:
            return
        try:
            db.session.rollback()  # type: ignore
        finally:
            # The rollback can discard identity changes. Resolve again.
            self._resolved_user_names.clear()

    @staticmethod
    def _session_has_changes() -> bool:
        session = db.session  # type: ignore
        if session.new or session.deleted:
            return True
        return any(session.is_modified(obj) for obj in session.dirty)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _handle_session_start(
        self, event: ActivityEvent, batch: _EventBatch | None = None
    ) -> ActivitySession:
        batch = batch or self._single_event_batch(event)
        existing_session = batch.find(event)

        if existing_session:
            self.logger.debug("Session %s already exists, updating", event.session_id)
            return self._update_existing_session(existing_session, event, batch)

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
        if event.state:
            metadata[PLAYBACK_STATE_KEY] = event.state
        session.set_metadata(metadata)

        self._assign_session_identity(session)

        db.session.add(session)  # type: ignore
        db.session.flush()  # type: ignore
        batch.wrote = True
        batch.active[batch.key(event)] = session
        self._remember_user_name(session.id, event.user_name)

        self._apply_session_grouping(session, event)

        if event.position_ms is not None and event.state:
            self._create_snapshot(session.id, event)

        self.logger.info(
            "Started tracking session %s for user %s",
            event.session_id,
            event.user_name,
        )
        return session

    def _handle_session_update(
        self, event: ActivityEvent, batch: _EventBatch | None = None
    ) -> ActivitySession | None:
        batch = batch or self._single_event_batch(event)
        session = batch.find(event)

        if not session:
            self.logger.debug(
                "Session %s not found for update, creating new session",
                event.session_id,
            )
            event.event_type = "session_start"
            return self._handle_session_start(event, batch)

        return self._update_existing_session(session, event, batch)

    def _handle_session_end(
        self, event: ActivityEvent, batch: _EventBatch | None = None
    ) -> ActivitySession | None:
        batch = batch or self._single_event_batch(event)
        session = batch.find(event)

        if not session:
            self.logger.debug(
                "Session %s not found for end event, skipping", event.session_id
            )
            return None

        self._update_session_from_event(session, event)
        self._resolve_unlinked_user(session, event)

        # The session ends at the event time. After a long outage of the
        # media server, the collector sends the time of its last successful
        # poll, which is earlier than now.
        ended_at = _as_utc(event.timestamp)
        if ended_at is not None and ended_at < _as_utc(session.updated_at):
            session.updated_at = ended_at

        session.active = False
        metadata = session.get_metadata()
        if event.timestamp:
            metadata["last_end_timestamp"] = event.timestamp.isoformat()
        metadata["status"] = "ended"
        if event.state:
            metadata[PLAYBACK_STATE_KEY] = event.state
        session.set_metadata(metadata)

        if event.position_ms is not None:
            self._create_snapshot(session.id, event)

        batch.wrote = True
        batch.active.pop(batch.key(event), None)
        self._resolved_user_names.pop(session.id, None)

        self.logger.info(
            "Closed session %s for user %s", event.session_id, event.user_name
        )
        return session

    def _single_event_batch(self, event: ActivityEvent) -> _EventBatch:
        """Return a batch for a direct handler call (outside record_activity_events)."""
        batch = _EventBatch()
        batch.load([event])
        return batch

    # ------------------------------------------------------------------
    # Update logic
    # ------------------------------------------------------------------
    def _update_existing_session(
        self,
        session: ActivitySession,
        event: ActivityEvent,
        batch: _EventBatch,
    ) -> ActivitySession:
        """
        Apply an event to an active session and write only when necessary.

        A meaningful change (state, user, media, device, stream decision) is
        written at once. A change in the position or the elapsed time only is
        written at most once per POSITION_PERSIST_INTERVAL.
        """
        now = datetime.now(UTC)
        metadata = session.get_metadata()
        state_changed = bool(event.state) and event.state != metadata.get(
            PLAYBACK_STATE_KEY
        )
        meaningful = state_changed

        name_resolved = False
        if (
            _is_known(event.user_name)
            and self._resolved_user_names.get(session.id) != event.user_name
        ):
            meaningful |= self._apply_user_name(session, event.user_name)
            name_resolved = True

        if event.user_id and session.user_id != str(event.user_id):
            session.user_id = str(event.user_id)
            meaningful = True

        for attribute in ("media_title", "device_name", "client_name", "platform"):
            value = getattr(event, attribute)
            if _is_known(value) and getattr(session, attribute) != value:
                self.logger.debug(
                    "Enriching session %s %s: %s -> %s",
                    event.session_id,
                    attribute,
                    getattr(session, attribute),
                    value,
                )
                setattr(session, attribute, value)
                meaningful = True

        if (
            event.media_type
            and event.media_type.lower() != "unknown"
            and session.media_type != event.media_type
        ):
            session.media_type = event.media_type
            meaningful = True

        if event.media_id and session.media_id != str(event.media_id):
            session.media_id = str(event.media_id)
            meaningful = True

        new_metadata = self._merged_metadata(metadata, event)
        if _without(new_metadata, VOLATILE_METADATA_KEYS) != _without(
            metadata, VOLATILE_METADATA_KEYS
        ):
            meaningful = True
        volatile_changed = new_metadata != metadata

        new_transcoding = None
        if event.transcoding_info:
            event_transcoding = _as_stored(event.transcoding_info)
            current_transcoding = session.get_transcoding_info()
            if _without(event_transcoding, VOLATILE_TRANSCODING_KEYS) != _without(
                current_transcoding, VOLATILE_TRANSCODING_KEYS
            ):
                meaningful = True
            if event_transcoding != current_transcoding:
                new_transcoding = event.transcoding_info
                volatile_changed = True

        new_duration = self._event_duration(event, new_metadata)
        if new_duration is not None and new_duration != session.duration_ms:
            volatile_changed = True

        last_write = _as_utc(session.updated_at)
        age = now - last_write if last_write else KEEPALIVE_INTERVAL

        if not (
            meaningful
            or (volatile_changed and age >= POSITION_PERSIST_INTERVAL)
            or age >= KEEPALIVE_INTERVAL
        ):
            return session

        if not name_resolved:
            self._resolve_unlinked_user(session, event)

        if new_metadata != metadata:
            session.set_metadata(new_metadata)
        if new_transcoding is not None:
            session.set_transcoding_info(new_transcoding)
        if new_duration is not None:
            session.duration_ms = new_duration
        session.updated_at = now
        batch.wrote = True

        if state_changed and event.position_ms is not None:
            self._create_snapshot(session.id, event)

        return session

    def _resolve_unlinked_user(
        self, session: ActivitySession, event: ActivityEvent
    ) -> None:
        """Resolve the user again when the session has no Wizarr user.

        The user can be created or linked after the session starts. The
        service calls this method only when it writes the session, and the
        identity cache keeps the cost low.
        """
        if session.wizarr_user_id is None and _is_known(event.user_name):
            self._apply_user_name(session, event.user_name)

    def _apply_user_name(self, session: ActivitySession, raw_name: str) -> bool:
        """Resolve a media server user name. Return True when the session changed."""
        try:
            user_id, identity_id, display_name = resolve_user_identity_cached(
                session.server_id, raw_name
            )
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.debug("Identity resolution skipped: %s", exc)
            user_id, identity_id, display_name = None, None, raw_name

        changed = False
        if user_id and session.wizarr_user_id != user_id:
            session.wizarr_user_id = user_id
            changed = True
        if identity_id and session.wizarr_identity_id != identity_id:
            session.wizarr_identity_id = identity_id
            changed = True

        target_name = display_name or raw_name
        if session.user_name != target_name:
            self.logger.debug(
                "Enriching session %s user_name: %s -> %s",
                session.session_id,
                session.user_name,
                target_name,
            )
            session.user_name = target_name
            changed = True

        session._resolved_identity_name = target_name
        self._remember_user_name(session.id, raw_name)
        return changed

    def _remember_user_name(self, session_row_id: int | None, raw_name: str) -> None:
        if session_row_id is None or not raw_name:
            return
        if len(self._resolved_user_names) >= _MAX_REMEMBERED_SESSIONS:
            self._resolved_user_names.clear()
        self._resolved_user_names[session_row_id] = raw_name

    def _merged_metadata(
        self, metadata: dict[str, Any], event: ActivityEvent
    ) -> dict[str, Any]:
        new_metadata = dict(metadata)
        if event.position_ms is not None:
            new_metadata["last_known_position_ms"] = event.position_ms
        if event.metadata:
            new_metadata.update(event.metadata)
        if event.state:
            new_metadata[PLAYBACK_STATE_KEY] = event.state
        return _as_stored(new_metadata)

    def _event_duration(
        self,
        event: ActivityEvent,
        metadata: dict[str, Any],
    ) -> int | None:
        if event.duration_ms is not None:
            return event.duration_ms

        total_duration_seconds = metadata.get("total_duration_seconds")
        if total_duration_seconds is None:
            return None
        try:
            return max(int(float(total_duration_seconds) * 1000), 0)
        except (TypeError, ValueError):
            self.logger.debug(
                "Invalid total_duration_seconds value: %s", total_duration_seconds
            )
            return None

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
        """Group sessions that belong together despite different sessionKeys."""
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

            if prev_timestamp is None or event_timestamp is None:
                # The history grid groups on reference_id. Each session must
                # have one.
                new_session.reference_id = new_session.id
                return

            # Normalize both timestamps to UTC properly
            if prev_timestamp.tzinfo is None:
                prev_timestamp = prev_timestamp.replace(tzinfo=UTC)
            else:
                prev_timestamp = prev_timestamp.astimezone(UTC)

            if event_timestamp.tzinfo is None:
                event_timestamp = event_timestamp.replace(tzinfo=UTC)
            else:
                event_timestamp = event_timestamp.astimezone(UTC)

            time_gap = event_timestamp - prev_timestamp
            gap_seconds = time_gap.total_seconds()

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
        """Find previous sessions to group using fallback matching strategies."""
        base_query = db.session.query(ActivitySession).filter(  # type: ignore
            ActivitySession.server_id == server_id,
            ActivitySession.user_name == user_name,
            ActivitySession.id < current_session_id,
        )

        # Try media_id match first
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
                    return exact_matches

        # Fallback to title + device match
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
                    return title_device_matches

        # Last resort: title-only match
        return (
            base_query.filter(ActivitySession.media_title == media_title)
            .order_by(ActivitySession.id.desc())
            .limit(2)
            .all()
        )

    def _update_session_from_event(
        self,
        session: ActivitySession,
        event: ActivityEvent,
    ) -> ActivitySession:
        """Apply position, metadata, duration and stream data without a throttle."""
        metadata = session.get_metadata()
        if event.position_ms is not None:
            metadata["last_known_position_ms"] = event.position_ms
        if event.metadata:
            metadata.update(event.metadata)

        duration_ms = self._event_duration(event, metadata)
        if duration_ms is not None:
            session.duration_ms = duration_ms

        if event.transcoding_info:
            session.set_transcoding_info(event.transcoding_info)

        session.set_metadata(metadata if metadata else {})

        session.updated_at = datetime.now(UTC)
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

        db.session.add(snapshot)  # type: ignore


__all__ = ["ActivityIngestionService"]
