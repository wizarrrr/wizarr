"""
Jellyfin activity collector using Sessions API polling.

Polls Jellyfin's Sessions API to monitor active playback sessions.
"""

from datetime import UTC, datetime
from typing import Any

from ...domain.models import ActivityEvent
from ..monitor import BaseCollector


class JellyfinCollector(BaseCollector):
    """Jellyfin activity collector using Sessions API polling."""

    def __init__(self, server, event_callback):
        super().__init__(server, event_callback)
        self.active_sessions: dict[str, dict[str, Any]] = {}

    def _collect_loop(self):
        """Main collection loop using Jellyfin Sessions API polling."""
        self.logger.info("Starting Jellyfin Sessions API polling")

        while self.running and not self._stop_event.is_set():
            try:
                client = self._get_media_client()
                if client:
                    self.logger.debug("Polling Jellyfin Sessions API...")
                    sessions = client.now_playing()

                    if sessions:
                        self.logger.info(f"Found {len(sessions)} active sessions")
                        for i, session in enumerate(sessions):
                            self.logger.debug(
                                f"Session {i + 1}: {session.get('user_name', 'Unknown')} - {session.get('media_title', 'Unknown')}"
                            )
                    else:
                        self.logger.debug("No active sessions found")

                    self._process_sessions(sessions)
                else:
                    self.logger.warning("Failed to get media client for polling")

                # Poll every 10 seconds for responsive monitoring
                self._stop_event.wait(10)

            except Exception as e:
                self.logger.error(f"Jellyfin API polling error: {e}", exc_info=True)
                self.error_count += 1
                self._stop_event.wait(30)  # Wait longer on error

    def _process_sessions(self, sessions):
        """Process sessions from Jellyfin API and emit events."""
        if not sessions:
            # All sessions ended
            for session_id in list(self.active_sessions.keys()):
                old_session = self.active_sessions.pop(session_id)
                self._emit_session_event(old_session, "session_end")
            return

        current_session_ids = set()

        for session_data in sessions:
            try:
                session_id = session_data.get("session_id", "")
                if not session_id:
                    continue

                current_session_ids.add(session_id)

                # Check if this is a new session or has changes
                if session_id not in self.active_sessions:
                    # New session
                    self.active_sessions[session_id] = session_data
                    self._emit_session_event(session_data, "session_start")
                else:
                    # Check for state changes
                    old_session = self.active_sessions[session_id]
                    self.active_sessions[session_id] = session_data

                    old_state = old_session.get("state", "playing")
                    new_state = session_data.get("state", "playing")

                    if old_state != new_state:
                        if new_state == "paused":
                            self._emit_session_event(session_data, "session_pause")
                        else:
                            self._emit_session_event(session_data, "session_resume")
                    else:
                        # Regular progress update
                        self._emit_session_event(session_data, "session_progress")

            except Exception as e:
                self.logger.error(f"Failed to process session: {e}", exc_info=True)

        # Remove ended sessions
        ended_sessions = set(self.active_sessions.keys()) - current_session_ids
        for session_id in ended_sessions:
            old_session = self.active_sessions.pop(session_id)
            self._emit_session_event(old_session, "session_end")

    def _emit_session_event(self, session_data: dict[str, Any], event_type: str):
        """Convert session data to ActivityEvent and emit."""
        try:
            event = ActivityEvent(
                event_type=event_type,
                server_id=self.server.id,
                session_id=session_data.get("session_id", ""),
                user_name=session_data.get("user_name", "Unknown"),
                media_title=session_data.get("media_title", "Unknown"),
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
                transcoding_info=session_data.get("transcoding_info"),
                metadata=session_data.get("metadata"),
                artwork_url=session_data.get("artwork_url"),
                thumbnail_url=session_data.get("thumbnail_url"),
            )

            self._emit_event(event)

        except Exception as e:
            self.logger.error(
                f"Failed to emit Jellyfin session event: {e}", exc_info=True
            )

    def stop(self):
        """Stop the Jellyfin collector."""
        super().stop()
        self.logger.info("Jellyfin collector stopped")
