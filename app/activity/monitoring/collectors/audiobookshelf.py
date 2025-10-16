"""
Audiobookshelf activity collector using REST API polling for session monitoring.
"""

from datetime import UTC, datetime
from typing import Any

from ...domain.models import ActivityEvent
from ..monitor import BaseCollector


class AudiobookshelfCollector(BaseCollector):
    """Audiobookshelf activity collector using REST API polling for session monitoring."""

    def __init__(self, server, event_callback):
        super().__init__(server, event_callback)
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self.last_seen_sessions: set[str] = set()  # Track session IDs we've seen
        self.poll_interval = 30  # Poll every 30 seconds

    def _collect_loop(self):
        """Main collection loop using Audiobookshelf REST API polling."""
        self.logger.info(
            f"Starting Audiobookshelf REST API polling for {self.server.name}"
        )

        while self.running and not self._stop_event.is_set():
            try:
                # Get current sessions from API
                client = self._get_media_client()
                if client:
                    sessions = client.now_playing()
                    self._process_sessions(sessions)
                else:
                    self.logger.warning("No media client available")

                # Wait for next poll interval
                self._stop_event.wait(self.poll_interval)

            except Exception as e:
                self.logger.error(f"Audiobookshelf polling error: {e}")
                self.error_count += 1

                # Wait longer on error
                self._stop_event.wait(min(60, self.poll_interval * 2))

    def _process_sessions(self, sessions):
        """Process current sessions from REST API."""
        self.logger.debug(f"Processing {len(sessions)} sessions from API")

        if not sessions:
            # No active sessions - check for session ends
            self._handle_no_active_sessions()
            return

        # Log first session for debugging
        if sessions:
            self.logger.info(
                f"Sample session data: {sessions[0]}"
            )  # Changed to info level for debugging

        current_session_ids = set()

        for session_data in sessions:
            try:
                session_id = session_data.get("session_id")
                if not session_id:
                    self.logger.warning(f"Session missing session_id: {session_data}")
                    continue

                current_session_ids.add(session_id)

                # Check if this is a new session
                is_new_session = session_id not in self.last_seen_sessions

                if is_new_session:
                    self.logger.info(
                        f"🎬 New session started: {session_id} for user {session_data.get('user_name', 'Unknown')}"
                    )
                    self._emit_session_event(session_data, "session_start")
                    self.last_seen_sessions.add(session_id)
                else:
                    # Existing session - emit progress event
                    self._emit_session_event(session_data, "session_progress")

                # Update our tracking
                self.active_sessions[session_id] = session_data

            except Exception as e:
                self.logger.error(f"Error processing session: {e}")

        # Check for ended sessions
        ended_sessions = self.last_seen_sessions - current_session_ids
        for session_id in ended_sessions:
            self.logger.info(f"🛑 Session ended: {session_id}")

            # Get the last known session data if available
            if session_id in self.active_sessions:
                session_data = self.active_sessions.pop(session_id)
                self._emit_session_event(session_data, "session_end")

            self.last_seen_sessions.discard(session_id)

    def _handle_no_active_sessions(self):
        """Handle the case where there are no active sessions."""
        # If we had active sessions before and now we don't, they ended
        for session_id in list(self.last_seen_sessions):
            self.logger.info(f"🛑 Session ended (no active sessions): {session_id}")

            if session_id in self.active_sessions:
                session_data = self.active_sessions.pop(session_id)
                self._emit_session_event(session_data, "session_end")

        self.last_seen_sessions.clear()
        self.active_sessions.clear()

    def _extract_session_data_from_polling(
        self, session_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract and standardize session data from REST API polling response."""
        try:
            metadata = session_data.get("metadata", {}) or {}
            # Prefer human-friendly usernames when available
            user_name = (
                session_data.get("user_name")
                or metadata.get("username")
                or metadata.get("user_name")
                or metadata.get("display_name")
                or session_data.get("user_id")
                or "Unknown"
            )

            # The now_playing() method returns session data with these field names
            return {
                "session_id": session_data.get("session_id", ""),
                "user_name": user_name,
                "user_id": session_data.get(
                    "user_id"
                ),  # This might not be in the response
                "media_title": session_data.get("media_title", "Unknown"),
                "media_type": session_data.get("media_type", "audiobook"),
                "media_id": session_data.get("media_id"),
                "series_name": session_data.get("series_name"),
                "duration_ms": session_data.get("duration_ms", 0),
                "position_ms": session_data.get("position_ms", 0),
                "device_name": session_data.get("device_name", "Unknown Device"),
                "client_name": session_data.get("client", "Audiobookshelf"),
                "state": session_data.get("state", "playing"),
                "artwork_url": session_data.get("artwork_url"),
                "thumbnail_url": session_data.get("thumbnail_url"),
                "metadata": {
                    "audiobookshelf_session_id": session_data.get("session_id", ""),
                    "transcoding": session_data.get("transcoding", {}),
                    **metadata,
                },
            }
        except Exception as e:
            self.logger.error(f"Error extracting session data: {e}")
            return {}

    def _emit_session_event(self, session_data: dict[str, Any], event_type: str):
        """Convert session data to ActivityEvent and emit."""
        try:
            # Extract data from polling response or use standardized format
            extracted_data = self._extract_session_data_from_polling(session_data)

            if not extracted_data:
                self.logger.warning("No extracted data available for event emission")
                return

            event = ActivityEvent(
                event_type=event_type,
                server_id=self.server.id,
                session_id=extracted_data["session_id"],
                user_name=extracted_data["user_name"],
                media_title=extracted_data["media_title"],
                timestamp=datetime.now(UTC),
                user_id=extracted_data.get("user_id"),
                media_type=extracted_data.get("media_type"),
                media_id=extracted_data.get("media_id"),
                series_name=extracted_data.get("series_name"),
                duration_ms=extracted_data.get("duration_ms"),
                position_ms=extracted_data.get("position_ms"),
                device_name=extracted_data.get("device_name"),
                client_name=extracted_data.get("client_name"),
                state=extracted_data.get("state"),
                artwork_url=extracted_data.get("artwork_url"),
                thumbnail_url=extracted_data.get("thumbnail_url"),
                metadata=extracted_data.get("metadata"),
            )

            self.logger.info(
                f"📤 About to emit event: server_id={self.server.id}, server_name={self.server.name}, user={extracted_data['user_name']}, media={extracted_data['media_title']}"
            )
            self._emit_event(event)
            self.logger.info(
                f"✅ Emitted {event_type} event for session {extracted_data['session_id']}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to emit Audiobookshelf session event: {e}", exc_info=True
            )
