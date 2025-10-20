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

        # Update session tracking
        with self._lock:
            if session_key not in self.active_sessions:
                self.active_sessions[session_key] = {
                    "session_key": session_key,
                    "started_at": transition.timestamp,
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
                self.active_sessions[session_key].update(
                    {
                        "state": to_state.value,
                        "view_offset": transition.view_offset,
                        "last_updated": transition.timestamp,
                    }
                )

        # Handle specific state transitions
        if from_state is None and to_state == SessionState.PLAYING:
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
        """Handle session start with rich logging and validation."""
        session_key = transition.session_key
        server_id = (
            transition.metadata.get("server_id") if transition.metadata else None
        )

        self.logger.info(
            f"🎬 Session start handler called for {session_key}, server_id={server_id}"
        )

        # Retry logic for session data lookup
        session_data = {}
        max_retries = 3
        retry_delay = 0.5  # 0.5 seconds between retries

        for attempt in range(max_retries):
            session_data = self._get_session_from_current_activity(
                session_key, server_id
            )

            # Check if we got valid session data (all critical fields populated)
            if (
                session_data.get("username") != "Unknown"
                and session_data.get("full_title") != "Unknown"
                and session_data.get("device") != "Unknown"
            ):
                break

            if attempt < max_retries - 1:  # Don't sleep after last attempt
                self.logger.debug(
                    f"Session data not ready for {session_key}, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})"
                )
                import time

                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

        user_name = session_data.get("username", "Unknown")
        media_title = session_data.get("full_title", "Unknown")
        device_name = session_data.get("device", "Unknown")
        rating_key = (
            transition.metadata.get("rating_key") if transition.metadata else None
        )

        # If we still have Unknown data after retries, log a warning but continue
        if (
            user_name == "Unknown"
            or media_title == "Unknown"
            or device_name == "Unknown"
        ):
            self.logger.warning(
                f"⚠️  Session {session_key} still has incomplete data after {max_retries} retries "
                f"(user={user_name}, title={media_title}, device={device_name}) - creating session anyway"
            )

        self.logger.info(
            f"🎬 Session {session_key} started for user {user_name}, title: {media_title} (rating_key: {rating_key})"
        )

        # Cache the session data including timestamp for duration calculation
        with self._lock:
            self.active_sessions[session_key] = {
                **session_data,
                "started_at": transition.timestamp,
                "last_update": transition.timestamp,
            }

        # Create activity event with rich data from session
        event = ActivityEvent(
            event_type="session_start",
            server_id=int(transition.metadata.get("server_id", 0))
            if transition.metadata
            else 0,
            session_id=session_key,
            user_name=user_name,
            user_id=session_data.get("user_id"),
            media_title=media_title,
            media_type=session_data.get("media_type", "unknown"),
            media_id=session_data.get("rating_key", rating_key),
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
        """Handle session resume with pause duration tracking."""
        session_key = transition.session_key
        self.logger.info(
            f"▶️ Session {session_key} resumed from {transition.view_offset}ms"
        )

        # Calculate pause duration
        pause_duration = None
        with self._lock:
            if session_key in self.active_sessions:
                paused_at = self.active_sessions[session_key].get("paused_at")
                if paused_at:
                    pause_duration = (transition.timestamp - paused_at).total_seconds()
                    self.active_sessions[session_key].pop("paused_at", None)

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

        # Clean up session tracking
        with self._lock:
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

        # Calculate total duration
        started_at = session_data.get("started_at")
        total_duration = None
        duration_ms = None
        if started_at:
            total_duration = (transition.timestamp - started_at).total_seconds()
            if total_duration is not None:
                try:
                    duration_ms = max(int(total_duration * 1000), 0)
                except (TypeError, ValueError):
                    duration_ms = None

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
                "total_duration_seconds": total_duration,
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
        """Record periodic progress snapshots."""
        # Only record progress snapshots every 30 seconds to avoid spam
        session_key = transition.session_key
        with self._lock:
            session_data = self.active_sessions.get(session_key, {})
            last_progress = session_data.get(
                "last_progress_recorded", datetime.min.replace(tzinfo=UTC)
            )

        if (transition.timestamp - last_progress).total_seconds() >= 30:
            # Get complete session data for progress event
            server_id = (
                int(transition.metadata.get("server_id", 0))
                if transition.metadata
                else 0
            )
            session_data = self._get_session_from_current_activity(
                session_key, server_id
            )

            event = ActivityEvent(
                event_type="session_progress",
                server_id=server_id,
                session_id=session_key,
                user_name=session_data.get("username", "Unknown"),
                media_title=session_data.get("full_title", "Unknown"),
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
        self, alert_data: dict[str, Any], server_id: int
    ) -> bool:
        """Process timeline alerts (library changes, etc.)."""
        # For now, just log these - could be enhanced for library monitoring
        self.logger.debug(
            f"Timeline alert received: {alert_data.get('type', 'unknown')}"
        )
        return True

    def _process_transcode_start(
        self, alert_data: dict[str, Any], server_id: int
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
        self, alert_data: dict[str, Any], server_id: int
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
                from app.extensions import db
                from app.models import MediaServer, User
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
                self.logger.info(f"📡 Found {len(sessions)} active Plex sessions")

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

                # Extract session data (following Tautulli's pattern)
                session_data = {}

                # User information
                plex_username = None
                usernames = getattr(target_session, "usernames", None)
                users = getattr(target_session, "users", None)

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
                title = getattr(target_session, "title", "Unknown")
                grandparent_title = getattr(target_session, "grandparentTitle", None)
                parent_title = getattr(target_session, "parentTitle", None)

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
                session_data["media_type"] = getattr(target_session, "type", "unknown")
                session_data["rating_key"] = getattr(target_session, "ratingKey", "")
                session_data["session_key"] = session_key_attr

                # Extract player/device info properly
                player_obj = getattr(target_session, "player", None)
                if player_obj:
                    # player.product = client software (e.g., "Plex for iOS")
                    # player.title = device name (e.g., "iPhone", "Chrome")
                    # player.platform = platform (e.g., "iOS", "Chrome")
                    session_data["player"] = getattr(player_obj, "product", "Unknown")
                    session_data["device"] = getattr(player_obj, "title", "Unknown")
                    session_data["platform"] = getattr(
                        player_obj, "platform", "Unknown"
                    )
                else:
                    session_data["player"] = "Unknown"
                    session_data["device"] = "Unknown"
                    session_data["platform"] = "Unknown"

                self.logger.info(
                    f"📡 Retrieved complete session data for {session_key}: user={session_data['username']}, title={session_data['full_title']}"
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
