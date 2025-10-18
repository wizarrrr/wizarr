"""
Polling activity collector for media servers without WebSocket support.

Uses the existing now_playing() API methods to poll for active sessions
on servers that don't support real-time WebSocket notifications.
"""

from datetime import UTC, datetime
from typing import Any

from ...domain.models import ActivityEvent
from ..monitor import BaseCollector


class PollingCollector(BaseCollector):
    """Generic polling collector for servers without WebSocket support."""

    def __init__(self, server, event_callback):
        super().__init__(server, event_callback)
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self.poll_interval = 30  # seconds

    def _collect_loop(self):
        """Main collection loop using polling."""
        self.logger.info(f"Starting polling collector for {self.server.name}")

        while self.running and not self._stop_event.is_set():
            try:
                self._poll_sessions()
                self._stop_event.wait(self.poll_interval)

            except Exception as e:
                self.logger.error(f"Polling error: {e}", exc_info=True)
                self.error_count += 1
                # Wait longer on error
                self._stop_event.wait(60)

    def _poll_sessions(self):
        """Poll server for current sessions."""
        try:
            client = self._get_media_client()
            if not client:
                self.logger.warning("No media client available for polling")
                return

            # Get current sessions from server
            current_sessions = client.now_playing()
            current_session_ids = set()

            # Process each current session
            for session_data in current_sessions:
                session_id = session_data.get("session_id", "")
                if not session_id:
                    continue

                current_session_ids.add(session_id)

                # Check if this is a new session
                if session_id not in self.active_sessions:
                    # New session started
                    self.active_sessions[session_id] = session_data
                    self._emit_polling_event(session_data, "session_start")
                else:
                    # Existing session - check for changes
                    old_session = self.active_sessions[session_id]
                    self.active_sessions[session_id] = session_data

                    # Check for state changes
                    old_state = old_session.get("state", "unknown")
                    new_state = session_data.get("state", "unknown")

                    if old_state != new_state:
                        if new_state == "paused":
                            self._emit_polling_event(session_data, "session_pause")
                        elif new_state == "playing" and old_state == "paused":
                            self._emit_polling_event(session_data, "session_resume")
                        else:
                            self._emit_polling_event(session_data, "session_progress")
                    else:
                        # Regular progress update
                        self._emit_polling_event(session_data, "session_progress")

            # Find sessions that ended (no longer in current list)
            ended_sessions = set(self.active_sessions.keys()) - current_session_ids
            for session_id in ended_sessions:
                old_session = self.active_sessions.pop(session_id)
                self._emit_polling_event(old_session, "session_end")

        except Exception as e:
            self.logger.error(f"Failed to poll sessions: {e}", exc_info=True)
            self.error_count += 1

    def _emit_polling_event(self, session_data: dict[str, Any], event_type: str):
        """Convert polling session data to ActivityEvent and emit."""
        try:
            # Map common session data fields
            session_id = session_data.get("session_id", "")
            user_name = session_data.get("user_name", "Unknown")
            media_title = session_data.get("media_title", "Unknown")

            # Create activity event
            event = ActivityEvent(
                event_type=event_type,
                server_id=self.server.id,
                session_id=session_id,
                user_name=user_name,
                media_title=media_title,
                timestamp=datetime.now(UTC),
                user_id=session_data.get("user_id"),
                media_type=session_data.get("media_type"),
                media_id=session_data.get("media_id"),
                series_name=session_data.get("series_name"),
                season_number=session_data.get("season_number"),
                episode_number=session_data.get("episode_number"),
                duration_ms=session_data.get("duration_ms"),
                position_ms=session_data.get("position_ms"),
                device_name=session_data.get("device_name"),
                client_name=session_data.get("client"),
                ip_address=session_data.get("ip_address"),
                platform=session_data.get("platform"),
                player_version=session_data.get("player_version"),
                state=session_data.get("state", "playing"),
                transcoding_info=session_data.get("transcoding", {}),
                metadata=session_data.get("metadata", {}),
                artwork_url=session_data.get("artwork_url"),
                thumbnail_url=session_data.get("thumbnail_url"),
            )

            self._emit_event(event)

        except Exception as e:
            self.logger.error(f"Failed to emit polling event: {e}", exc_info=True)
