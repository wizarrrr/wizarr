"""
Enhanced session management inspired by Tautulli's robust approach.

This module provides sophisticated session lifecycle management with
state tracking, automatic cleanup, and intelligent session grouping.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from threading import Lock
from typing import Any

import structlog

from ..domain.models import ActivityEvent


class SessionState(Enum):
    """Possible session states."""

    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    BUFFERING = "buffering"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class SessionTransition:
    """Represents a state transition for a session."""

    session_key: str
    from_state: SessionState | None
    to_state: SessionState
    timestamp: datetime
    view_offset: int | None = None
    metadata: dict[str, Any] | None = None


class SessionManager:
    """
    Enhanced session manager with state tracking and lifecycle management.

    Inspired by Tautulli's robust session handling with automatic cleanup,
    state transitions, and intelligent session grouping.
    """

    def __init__(self, event_callback=None):
        self.logger = structlog.get_logger(__name__)
        self.event_callback = event_callback  # Callback to emit events properly
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self.session_timers: dict[str, Any] = {}
        self._lock = Lock()  # Protect shared state from race conditions
        self.cleanup_interval = 300  # 5 minutes stale session cleanup

    def process_alert(self, alert_data: dict[str, Any], server_id: int) -> bool:
        """
        Process a Plex alert with sophisticated state management.

        Args:
            alert_data: Raw alert data from Plex WebSocket
            server_id: Media server ID

        Returns:
            True if alert was processed successfully
        """
        try:
            alert_type = alert_data.get("type")

            if alert_type == "playing":
                return self._process_playing_alert(alert_data, server_id)
            if alert_type == "transcodeSession.start":
                return self._process_transcode_start(alert_data, server_id)
            if alert_type == "transcodeSession.end":
                return self._process_transcode_end(alert_data, server_id)
            if alert_type in [
                "activity",
                "status",
                "timeline",
                "transcodeSession.update",
                "update.statechange",
            ]:
                # Filter out noisy alerts completely
                return True
            self.logger.debug(f"Ignoring alert type: {alert_type}")
            return True

        except Exception as e:
            self.logger.error(f"Error processing alert: {e}", exc_info=True)
            return False

    def _process_playing_alert(
        self, alert_data: dict[str, Any], server_id: int
    ) -> bool:
        """Process playing state notifications with state machine logic."""
        notifications = alert_data.get("PlaySessionStateNotification", [])
        if not isinstance(notifications, list):
            notifications = [notifications]

        for notification in notifications:
            session_key = notification.get("sessionKey")
            if not session_key:
                continue

            try:
                session_key = str(session_key)
                new_state = self._map_plex_state(notification.get("state", "unknown"))
                view_offset = notification.get("viewOffset", 0)
                rating_key = notification.get("ratingKey")

                # Get current session state
                with self._lock:
                    current_session = self.active_sessions.get(session_key)
                    last_state = None

                    if current_session:
                        last_state = SessionState(
                            current_session.get("state", "unknown")
                        )

                # Create state transition
                transition = SessionTransition(
                    session_key=session_key,
                    from_state=last_state,
                    to_state=new_state,
                    timestamp=datetime.now(UTC),
                    view_offset=view_offset,
                    metadata={
                        "rating_key": rating_key,
                        "server_id": server_id,
                        "raw_alert": notification,
                    },
                )

                # Process the state transition
                self._handle_state_transition(transition)

                # Reset cleanup timer
                self._schedule_cleanup(session_key)

            except Exception as e:
                self.logger.error(
                    f"Error processing playing alert for session {session_key}: {e}"
                )
                continue

        return True

    def _handle_state_transition(self, transition: SessionTransition):
        """
        Handle state transitions with sophisticated logic.

        This is inspired by Tautulli's state machine approach.
        """
        session_key = transition.session_key
        from_state = transition.from_state
        to_state = transition.to_state

        self.logger.debug(
            f"Session {session_key} transition: {from_state} -> {to_state}"
        )

        # Check if this is truly a new session or a duplicate alert BEFORE updating
        with self._lock:
            session_exists = session_key in self.active_sessions
            if session_exists:
                session_already_started = (
                    self.active_sessions[session_key].get("started_at") is not None
                )
            else:
                session_already_started = False

        # Update session tracking
        with self._lock:
            if not session_exists:
                # New session - create minimal tracking (started_at will be set by _on_session_start)
                self.active_sessions[session_key] = {
                    "session_key": session_key,
                    "started_at": None,  # Will be set by _on_session_start to avoid duplicates
                    "state": to_state.value,
                    "view_offset": transition.view_offset,
                    "server_id": transition.metadata.get("server_id")
                    if transition.metadata
                    else None,
                    "rating_key": transition.metadata.get("rating_key")
                    if transition.metadata
                    else None,
                    "last_updated": transition.timestamp,
                }
            else:
                # Existing session - just update state and offset
                self.active_sessions[session_key].update(
                    {
                        "state": to_state.value,
                        "view_offset": transition.view_offset,
                        "last_updated": transition.timestamp,
                    }
                )

        # Handle specific state transitions

        if from_state is None and to_state == SessionState.PLAYING:
            if session_already_started:
                # This is a duplicate start alert - Plex sometimes sends these
                self.logger.debug(
                    f"🔄 Duplicate start alert for session {session_key} - treating as progress update"
                )
                # Don't call _on_session_start again, just update progress
            else:
                # Double-check right before starting to handle race conditions
                with self._lock:
                    # Check if another thread just started this session
                    currently_started = (
                        session_key in self.active_sessions
                        and self.active_sessions[session_key].get("started_at")
                        is not None
                    )

                if currently_started:
                    self.logger.debug(
                        f"🔄 Race condition detected - session {session_key} already started by another thread"
                    )
                else:
                    self._on_session_start(transition)
        elif from_state == SessionState.PLAYING and to_state == SessionState.PAUSED:
            self._on_session_pause(transition)
        elif from_state == SessionState.PAUSED and to_state == SessionState.PLAYING:
            self._on_session_resume(transition)
        elif to_state == SessionState.STOPPED:
            self._on_session_stop(transition)
        elif to_state == SessionState.BUFFERING:
            self._on_session_buffer(transition)
        elif to_state == SessionState.ERROR:
            self._on_session_error(transition)

        # Always record progress for playing/paused states
        if to_state in (SessionState.PLAYING, SessionState.PAUSED):
            self._record_progress(transition)

    def _on_session_start(self, transition: SessionTransition):
        """Handle session start with IMMEDIATE enrichment (Tautulli approach)."""
        session_key = transition.session_key
        server_id = (
            transition.metadata.get("server_id") if transition.metadata else None
        )

        self.logger.info(
            f"🎬 Session {session_key} started - fetching complete data immediately"
        )

        # ✅ TAUTULLI APPROACH: Fetch complete data IMMEDIATELY on start
        # This eliminates the "Unknown" value problem at the source
        session_data = self._get_session_from_current_activity(session_key, server_id)

        # Only fall back to "Unknown" if API call truly failed
        if not session_data or session_data.get("username") == "Unknown":
            self.logger.warning(
                f"⚠️ Could not enrich session {session_key} on start - using minimal data"
            )
            rating_key = (
                transition.metadata.get("rating_key") if transition.metadata else None
            )
            session_data = {
                "username": "Unknown",
                "full_title": "Unknown",
                "device": "Unknown",
                "player": "Unknown",
                "platform": "Unknown",
                "media_type": "unknown",
                "rating_key": rating_key,
                "session_key": session_key,
                "user_id": None,
                "needs_enrichment": True,  # Mark for retry on next progress
            }
        else:
            self.logger.info(
                f"✅ Session {session_key} enriched immediately: "
                f"user={session_data['username']}, title={session_data['full_title']}"
            )
            session_data["needs_enrichment"] = False

        # Cache the session data
        with self._lock:
            self.active_sessions[session_key] = {
                **session_data,
                "started_at": transition.timestamp,
                "last_update": transition.timestamp,
                "state": "playing",
                "paused_counter": 0,  # Track total time spent paused (Tautulli approach)
                "paused_at": None,  # Track when last paused
            }

        # Create activity event with enriched data
        event = ActivityEvent(
            event_type="session_start",
            server_id=int(transition.metadata.get("server_id", 0))
            if transition.metadata
            else 0,
            session_id=session_key,
            user_name=str(session_data.get("username", "Unknown")),
            user_id=session_data.get("user_id"),
            media_title=str(session_data.get("full_title", "Unknown")),
            media_type=session_data.get("media_type", "unknown"),
            media_id=session_data.get("rating_key"),
            device_name=session_data.get("device", "Unknown"),
            client_name=session_data.get("player", "Unknown"),
            platform=session_data.get("platform", "Unknown"),
            timestamp=transition.timestamp,
            position_ms=transition.view_offset,
            metadata=transition.metadata,
        )

        # Record the event
        if self.event_callback:
            self.event_callback(event)

    def _on_session_pause(self, transition: SessionTransition):
        """Handle session pause with timestamp tracking."""
        session_key = transition.session_key
        self.logger.info(
            f"⏸️ Session {session_key} paused at {transition.view_offset}ms"
        )

        # Track pause timestamp for duration calculations
        with self._lock:
            if session_key in self.active_sessions:
                self.active_sessions[session_key]["paused_at"] = transition.timestamp

        # Get complete session data for pause event
        server_id = (
            int(transition.metadata.get("server_id", 0)) if transition.metadata else 0
        )
        session_data = self._get_session_from_current_activity(session_key, server_id)

        event = ActivityEvent(
            event_type="session_pause",
            server_id=server_id,
            session_id=session_key,
            user_name=session_data.get("username", "Unknown"),
            media_title=session_data.get("full_title", "Unknown"),
            timestamp=transition.timestamp,
            position_ms=transition.view_offset,
            metadata=transition.metadata,
        )

        if self.event_callback:
            self.event_callback(event)

    def _on_session_resume(self, transition: SessionTransition):
        """Handle session resume with pause duration tracking (Tautulli approach)."""
        session_key = transition.session_key
        self.logger.info(
            f"▶️ Session {session_key} resumed from {transition.view_offset}ms"
        )

        # Calculate pause duration and accumulate in paused_counter (Tautulli approach)
        pause_duration = None
        with self._lock:
            if session_key in self.active_sessions:
                paused_at = self.active_sessions[session_key].get("paused_at")
                if paused_at:
                    pause_duration = (transition.timestamp - paused_at).total_seconds()

                    # ✅ ACCUMULATE pause time in counter (Tautulli approach)
                    current_paused_counter = self.active_sessions[session_key].get(
                        "paused_counter", 0
                    )
                    self.active_sessions[session_key]["paused_counter"] = (
                        current_paused_counter + pause_duration
                    )

                    # Clear paused_at since we've resumed
                    self.active_sessions[session_key]["paused_at"] = None

                    self.logger.debug(
                        f"Session {session_key} was paused for {pause_duration:.1f}s, "
                        f"total paused: {self.active_sessions[session_key]['paused_counter']:.1f}s"
                    )

        # Get complete session data for resume event
        server_id = (
            int(transition.metadata.get("server_id", 0)) if transition.metadata else 0
        )
        session_data = self._get_session_from_current_activity(session_key, server_id)

        event = ActivityEvent(
            event_type="session_resume",
            server_id=server_id,
            session_id=session_key,
            user_name=session_data.get("username", "Unknown"),
            media_title=session_data.get("full_title", "Unknown"),
            timestamp=transition.timestamp,
            position_ms=transition.view_offset,
            metadata={**transition.metadata, "pause_duration_seconds": pause_duration},
        )

        if self.event_callback:
            self.event_callback(event)

    def _on_session_stop(self, transition: SessionTransition):
        """Handle session stop with cleanup and final recording."""
        session_key = transition.session_key
        server_id = (
            int(transition.metadata.get("server_id", 0)) if transition.metadata else 0
        )
        self.logger.info(
            f"⏹️ Session {session_key} stopped at {transition.view_offset}ms"
        )

        # Check if session exists
        with self._lock:
            if session_key not in self.active_sessions:
                self.logger.warning(
                    f"⚠️ Session {session_key} stop event received but session not found - "
                    f"likely stopped before start completed (race condition)"
                )
                # Cancel any pending timers just in case
                self._cancel_cleanup_timer(session_key)
                return

            session_data = self.active_sessions.pop(session_key, {})
        self._cancel_cleanup_timer(session_key)

        # Debug: Log what's in the cached session data
        self.logger.debug(
            f"🔍 Cached session data for {session_key}: username={session_data.get('username', 'missing')}, title={session_data.get('full_title', 'missing')}"
        )

        # Use cached data first (from session start), then try current activity as fallback
        # This is because stopped sessions are often already removed from Plex's active sessions
        current_session_data = session_data

        # If cached data is incomplete, try to get current session data
        if (
            not current_session_data
            or current_session_data.get("username") == "Unknown"
        ):
            self.logger.debug(
                f"🔍 Cached data incomplete for {session_key}, trying current activity lookup"
            )
            lookup_data = self._get_session_from_current_activity(
                session_key, server_id
            )
            if lookup_data and lookup_data.get("username") != "Unknown":
                self.logger.debug(
                    f"🔍 Current activity lookup successful for {session_key}: username={lookup_data.get('username')}"
                )
                current_session_data = lookup_data
            else:
                self.logger.debug(
                    f"🔍 Current activity lookup also failed for {session_key}"
                )

        user_name = current_session_data.get("username", "Unknown")
        media_title = current_session_data.get("full_title", "Unknown")

        # Calculate REAL play time (Tautulli approach)
        started_at = session_data.get("started_at")
        paused_counter = session_data.get("paused_counter", 0)
        paused_at = session_data.get("paused_at")

        # Handle stopped-while-paused case
        if paused_at:
            # User stopped while paused - add current pause to counter
            current_pause_duration = (transition.timestamp - paused_at).total_seconds()
            paused_counter += current_pause_duration
            self.logger.debug(
                f"Session {session_key} stopped while paused, "
                f"adding {current_pause_duration:.1f}s to paused_counter"
            )

        real_play_time = None
        duration_ms = None
        if started_at:
            # Total elapsed time
            elapsed_time = (transition.timestamp - started_at).total_seconds()

            # Real play time = elapsed time - time spent paused
            real_play_time = elapsed_time - paused_counter

            # Ensure non-negative
            real_play_time = max(real_play_time, 0)

            # Filter out very short sessions (< 10 seconds) - likely testing or accidental starts
            # This follows Tautulli's approach of ignoring very brief sessions
            MIN_SESSION_DURATION = 10  # seconds
            if real_play_time < MIN_SESSION_DURATION:
                self.logger.info(
                    f"🚫 Session {session_key} too short ({real_play_time:.1f}s < {MIN_SESSION_DURATION}s) - "
                    f"ignoring session (likely accidental start/stop)"
                )
                # Don't emit the session_end event for very short sessions
                return

            if real_play_time is not None:
                try:
                    duration_ms = max(int(real_play_time * 1000), 0)
                except (TypeError, ValueError):
                    duration_ms = None

            self.logger.info(
                f"📊 Session {session_key} duration: "
                f"elapsed={elapsed_time:.1f}s, paused={paused_counter:.1f}s, "
                f"real_play_time={real_play_time:.1f}s ({duration_ms}ms)"
            )

        event = ActivityEvent(
            event_type="session_end",
            server_id=server_id,
            session_id=session_key,
            user_name=user_name,
            media_title=media_title,
            media_type=current_session_data.get("media_type", "unknown"),
            media_id=current_session_data.get("rating_key"),
            device_name=current_session_data.get("device", "Unknown"),
            client_name=current_session_data.get("player", "Unknown"),
            platform=current_session_data.get("platform", "Unknown"),
            timestamp=transition.timestamp,
            position_ms=transition.view_offset,
            duration_ms=duration_ms,
            metadata={
                **transition.metadata,
                "real_play_time_seconds": real_play_time,
                "paused_counter_seconds": paused_counter,
                "elapsed_time_seconds": (
                    (transition.timestamp - started_at).total_seconds()
                    if started_at
                    else None
                ),
            },
        )

        if self.event_callback:
            self.event_callback(event)

    def _on_session_buffer(self, transition: SessionTransition):
        """Handle buffering events with frequency tracking."""
        session_key = transition.session_key

        # Track buffer events frequency
        with self._lock:
            if session_key in self.active_sessions:
                buffer_count = (
                    self.active_sessions[session_key].get("buffer_count", 0) + 1
                )
                self.active_sessions[session_key]["buffer_count"] = buffer_count

                # Only log excessive buffering
                if buffer_count >= 3:
                    self.logger.warning(
                        f"🔄 Session {session_key} buffering (count: {buffer_count})"
                    )

        # Get complete session data for buffer event
        server_id = (
            int(transition.metadata.get("server_id", 0)) if transition.metadata else 0
        )
        session_data = self._get_session_from_current_activity(session_key, server_id)

        event = ActivityEvent(
            event_type="session_buffer",
            server_id=server_id,
            session_id=session_key,
            user_name=session_data.get("username", "Unknown"),
            media_title=session_data.get("full_title", "Unknown"),
            timestamp=transition.timestamp,
            position_ms=transition.view_offset,
            metadata=transition.metadata,
        )

        if self.event_callback:
            self.event_callback(event)

    def _on_session_error(self, transition: SessionTransition):
        """Handle session errors."""
        session_key = transition.session_key
        self.logger.warning(f"❌ Session {session_key} encountered error")

        event = ActivityEvent(
            event_type="session_error",
            server_id=int(transition.metadata.get("server_id", 0))
            if transition.metadata
            else 0,
            session_id=session_key,
            user_name="Unknown",
            media_title="Unknown",
            timestamp=transition.timestamp,
            position_ms=transition.view_offset,
            metadata=transition.metadata,
        )

        if self.event_callback:
            self.event_callback(event)

    def _record_progress(self, transition: SessionTransition):
        """Record periodic progress snapshots with smart enrichment (Tautulli-inspired)."""
        session_key = transition.session_key
        with self._lock:
            cached_session = self.active_sessions.get(session_key, {})
            last_progress = cached_session.get(
                "last_progress_recorded", datetime.min.replace(tzinfo=UTC)
            )
            needs_enrichment = cached_session.get("needs_enrichment", False)

        # Smart enrichment strategy:
        # - If needs_enrichment: try every 10 seconds (fast retry for failed starts)
        # - If already enriched: only update every 30 seconds (normal progress tracking)
        retry_interval = 10 if needs_enrichment else 30
        time_since_progress = (transition.timestamp - last_progress).total_seconds()

        if time_since_progress >= retry_interval:
            server_id = (
                int(transition.metadata.get("server_id", 0))
                if transition.metadata
                else 0
            )

            session_data = cached_session

            # Only query API if we need enrichment or it's time for periodic update
            if needs_enrichment or time_since_progress >= 30:
                fresh_session_data = self._get_session_from_current_activity(
                    session_key, server_id
                )

                # Check if we got better data than what's cached
                if fresh_session_data:
                    has_improvements = (
                        fresh_session_data.get("username", "Unknown") != "Unknown"
                        or fresh_session_data.get("full_title", "Unknown") != "Unknown"
                        or fresh_session_data.get("device", "Unknown") != "Unknown"
                    )

                    if has_improvements:
                        if needs_enrichment:
                            self.logger.info(
                                f"✨ Successfully enriched session {session_key}: "
                                f"user={fresh_session_data.get('username')}, "
                                f"title={fresh_session_data.get('full_title')}"
                            )
                        else:
                            self.logger.debug(f"🔄 Updated session {session_key} data")

                        # Update cached session with enriched data
                        with self._lock:
                            if session_key in self.active_sessions:
                                self.active_sessions[session_key].update(
                                    fresh_session_data
                                )
                                self.active_sessions[session_key][
                                    "needs_enrichment"
                                ] = False
                                self.active_sessions[session_key]["enriched_at"] = (
                                    transition.timestamp
                                )

                        session_data = fresh_session_data
                    else:
                        # Use cached data if fresh lookup didn't help
                        session_data = cached_session
                else:
                    # API lookup failed, use cached data
                    if needs_enrichment:
                        self.logger.warning(
                            f"⚠️ Still unable to enrich session {session_key}, will retry"
                        )
                    session_data = cached_session

            # Create progress event with current data
            event = ActivityEvent(
                event_type="session_progress",
                server_id=server_id,
                session_id=session_key,
                user_name=session_data.get("username", "Unknown"),
                user_id=session_data.get("user_id"),
                media_title=session_data.get("full_title", "Unknown"),
                media_type=session_data.get("media_type", "unknown"),
                media_id=session_data.get("rating_key"),
                device_name=session_data.get("device", "Unknown"),
                client_name=session_data.get("player", "Unknown"),
                platform=session_data.get("platform", "Unknown"),
                timestamp=transition.timestamp,
                position_ms=transition.view_offset,
                state=transition.to_state.value,
                metadata=transition.metadata,
            )

            if self.event_callback:
                self.event_callback(event)
            with self._lock:
                if session_key in self.active_sessions:
                    self.active_sessions[session_key]["last_progress_recorded"] = (
                        transition.timestamp
                    )

    def _schedule_cleanup(self, session_key: str, timeout_minutes: int = 5):
        """Schedule automatic cleanup for stale sessions (Tautulli-inspired)."""
        # Cancel existing timer
        self._cancel_cleanup_timer(session_key)

        # Schedule new cleanup
        from threading import Timer

        timer = Timer(
            timeout_minutes * 60, self._force_stop_session, args=[session_key]
        )
        timer.start()
        with self._lock:
            self.session_timers[session_key] = timer

    def _cancel_cleanup_timer(self, session_key: str):
        """Cancel cleanup timer for a session."""
        with self._lock:
            timer = self.session_timers.pop(session_key, None)
        if timer:
            timer.cancel()

    def _force_stop_session(self, session_key: str):
        """Force stop a stale session (Tautulli-inspired)."""
        with self._lock:
            if session_key not in self.active_sessions:
                return
            session_data = self.active_sessions[session_key].copy()

        self.logger.warning(f"🧹 Force stopping stale session {session_key}")

        # Create a synthetic stop transition
        transition = SessionTransition(
            session_key=session_key,
            from_state=SessionState(session_data.get("state", "unknown")),
            to_state=SessionState.STOPPED,
            timestamp=datetime.now(UTC),
            view_offset=session_data.get("view_offset", 0),
            metadata={
                "server_id": session_data.get("server_id"),
                "rating_key": session_data.get("rating_key"),
                "force_stopped": True,
            },
        )

        self._handle_state_transition(transition)

    def _map_plex_state(self, plex_state: str) -> SessionState:
        """Map Plex state strings to our SessionState enum."""
        state_mapping = {
            "playing": SessionState.PLAYING,
            "paused": SessionState.PAUSED,
            "stopped": SessionState.STOPPED,
            "buffering": SessionState.BUFFERING,
            "error": SessionState.ERROR,
            "unknown": SessionState.UNKNOWN,
        }
        return state_mapping.get(plex_state.lower(), SessionState.UNKNOWN)

    def _process_timeline_alert(
        self, alert_data: dict[str, Any], _server_id: int
    ) -> bool:
        """Process timeline alerts (library changes, etc.)."""
        # For now, just log these - could be enhanced for library monitoring
        self.logger.debug(
            f"Timeline alert received: {alert_data.get('type', 'unknown')}"
        )
        return True

    def _process_transcode_start(
        self, alert_data: dict[str, Any], _server_id: int
    ) -> bool:
        """Process transcoding session start."""
        transcode_sessions = alert_data.get("TranscodeSession", [])
        if not isinstance(transcode_sessions, list):
            transcode_sessions = [transcode_sessions]

        for session in transcode_sessions:
            self.logger.info(
                f"🔄 Transcode session started: {session.get('key', 'unknown')}"
            )

        return True

    def _process_transcode_end(
        self, alert_data: dict[str, Any], _server_id: int
    ) -> bool:
        """Process transcoding session end."""
        transcode_sessions = alert_data.get("TranscodeSession", [])
        if not isinstance(transcode_sessions, list):
            transcode_sessions = [transcode_sessions]

        for session in transcode_sessions:
            self.logger.info(
                f"✅ Transcode session ended: {session.get('key', 'unknown')}"
            )

        return True

    def get_active_sessions(self) -> dict[str, dict[str, Any]]:
        """Get all currently active sessions."""
        with self._lock:
            return self.active_sessions.copy()

    def cleanup_all_sessions(self):
        """Clean up all active sessions (for shutdown)."""
        self.logger.info("Cleaning up all active sessions")

        with self._lock:
            session_keys = list(self.active_sessions.keys())

        for session_key in session_keys:
            self._cancel_cleanup_timer(session_key)

        with self._lock:
            self.active_sessions.clear()
            self.session_timers.clear()

    def _extract_session_data_from_plex(
        self, plex_session, server_id: int
    ) -> dict[str, Any]:
        """
        Extract complete session data from a PlexAPI session object.

        This is a reusable helper that parses Plex session objects into our
        normalized format. Used by both WebSocket and polling paths.

        Args:
            plex_session: PlexAPI session object
            server_id: Database ID of the media server

        Returns:
            dict: Normalized session data with all fields populated
        """
        from app.extensions import db
        from app.models import User

        session_data = {}
        session_key = str(getattr(plex_session, "sessionKey", ""))

        # User information
        plex_username = None
        usernames = getattr(plex_session, "usernames", None)
        users = getattr(plex_session, "users", None)

        if usernames:
            plex_username = usernames[0]
        elif users:
            plex_username = users[0].title

        # Map to local user
        if plex_username:
            local_user = (
                User.query.filter_by(server_id=server_id)
                .filter(
                    db.or_(
                        User.username == plex_username,
                        User.email == plex_username,
                    )
                )
                .first()
            )

            if local_user:
                session_data["username"] = local_user.username
                session_data["user_id"] = local_user.id
            else:
                session_data["username"] = plex_username
                session_data["user_id"] = None
        else:
            session_data["username"] = "Unknown"
            session_data["user_id"] = None

        # Media information (rich title like Tautulli)
        title = getattr(plex_session, "title", "Unknown")
        grandparent_title = getattr(plex_session, "grandparentTitle", None)
        parent_title = getattr(plex_session, "parentTitle", None)

        # Build full title
        if grandparent_title and parent_title:
            # TV Show: "Game of Thrones - Season 1 - Winter Is Coming"
            session_data["full_title"] = (
                f"{grandparent_title} - {parent_title} - {title}"
            )
        elif grandparent_title:
            # TV Show without season: "Game of Thrones - Winter Is Coming"
            session_data["full_title"] = f"{grandparent_title} - {title}"
        else:
            # Movie or other: "The Matrix"
            session_data["full_title"] = title

        # Additional metadata
        session_data["media_type"] = getattr(plex_session, "type", "unknown")
        session_data["rating_key"] = getattr(plex_session, "ratingKey", "")
        session_data["session_key"] = session_key

        # Extract player/device info properly
        player_obj = getattr(plex_session, "player", None)
        if player_obj:
            # player.product = client software (e.g., "Plex for iOS")
            # player.title = device name (e.g., "iPhone", "Chrome")
            # player.platform = platform (e.g., "iOS", "Chrome")
            session_data["player"] = getattr(player_obj, "product", "Unknown")
            session_data["device"] = getattr(player_obj, "title", "Unknown")
            session_data["platform"] = getattr(player_obj, "platform", "Unknown")
        else:
            session_data["player"] = "Unknown"
            session_data["device"] = "Unknown"
            session_data["platform"] = "Unknown"

        return session_data

    def _get_session_from_current_activity(
        self, session_key: str, server_id: int
    ) -> dict[str, Any]:
        """
        Get complete session data using Tautulli's approach.
        Makes one API call to /status/sessions and finds our session.
        """
        try:
            # Import Flask dependencies
            from flask import has_app_context

            def _do_session_lookup():
                """Helper function to perform the actual session lookup."""
                from app.models import MediaServer
                from app.services.media.service import get_client_for_media_server

                # Get the server
                server = MediaServer.query.get(server_id)
                if not server:
                    self.logger.warning(f"Server {server_id} not found")
                    return {}

                # Get the media client
                client = get_client_for_media_server(server)
                if not client or not hasattr(client, "server"):
                    self.logger.warning(f"No valid client for server {server_id}")
                    return {}

                # Get ALL current sessions from Plex (Tautulli approach)
                sessions = client.server.sessions()
                self.logger.debug(f"📡 Found {len(sessions)} active Plex sessions")

                # Find our specific session
                target_session = None
                for session in sessions:
                    session_key_attr = str(getattr(session, "sessionKey", ""))
                    if session_key_attr == str(session_key):
                        target_session = session
                        break

                if not target_session:
                    self.logger.warning(
                        f"Session {session_key} not found in current activity"
                    )
                    return {}

                # Extract session data using our reusable helper
                session_data = self._extract_session_data_from_plex(
                    target_session, server_id
                )

                self.logger.info(
                    f"📡 Retrieved complete session data for {session_key}: "
                    f"user={session_data.get('username', 'Unknown')}, "
                    f"title={session_data.get('full_title', 'Unknown')}"
                )
                return session_data

            # Check if we need app context or if we already have one
            if has_app_context():
                return _do_session_lookup()
            # Look for app in the websocket monitor that created this collector
            from .monitor import _app_instance

            app = _app_instance
            if app:
                with app.app_context():
                    return _do_session_lookup()
            else:
                self.logger.warning("📡 No app context available for session lookup")
                return {}

        except Exception as e:
            self.logger.warning(
                f"Failed to get session from current activity: {e}", exc_info=True
            )
            return {}
