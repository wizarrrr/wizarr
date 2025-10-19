"""
Plex activity collector using AlertListener for real-time monitoring.

Uses PlexAPI's AlertListener to receive real-time notifications about
playback events for efficient activity tracking.
"""

from datetime import UTC, datetime
from typing import Any

try:
    from plexapi.alert import AlertListener

    PLEXAPI_AVAILABLE = True
except ImportError:
    PLEXAPI_AVAILABLE = False

from ...domain.models import ActivityEvent
from ..monitor import BaseCollector
from ..session_manager import SessionManager

EXCLUDED_ALERT_TYPES = {
    "timeline",
    "activity",
    "status",
    "progress",
    "transcodeSession.update",
    "update.statechange",
    "provider.content.change",
    "backgroundProcessingQueue",
}


class PlexCollector(BaseCollector):
    """Plex activity collector using AlertListener for real-time events."""

    def __init__(self, server, event_callback):
        super().__init__(server, event_callback)
        self.alert_listener: AlertListener | None = None
        self.plex_server = None
        self.session_manager = SessionManager(event_callback=self._emit_event)

    def _collect_loop(self):
        """Main collection loop using Plex AlertListener."""
        if not PLEXAPI_AVAILABLE:
            self.logger.error("PlexAPI not available, falling back to polling")
            self._fallback_to_polling()
            return

        try:
            self.logger.info(f"Starting Plex collector for {self.server.name}")

            # Get Plex server instance
            self.logger.debug("Getting Plex media client...")
            client = self._get_media_client()
            if not client:
                self.logger.error("Failed to get Plex client - falling back to polling")
                self._fallback_to_polling()
                return

            self.logger.debug(f"Got Plex client: {client}")

            # Access the PlexServer instance from the client
            if hasattr(client, "server"):
                self.plex_server = client.server
                self.logger.debug(f"Got Plex server instance: {self.plex_server}")
            elif hasattr(client, "plex"):
                self.plex_server = client.plex
                self.logger.debug(
                    f"Got Plex server from client.plex: {self.plex_server}"
                )
            else:
                self.logger.error(
                    f"Cannot find Plex server instance in client: {type(client)}"
                )
                self._fallback_to_polling()
                return

            # Test server connection
            try:
                self.logger.debug("Testing Plex server connection...")
                account = self.plex_server.account()
                account_name = (
                    getattr(account, "username", "Unknown") if account else "Unknown"
                )
                self.logger.info(
                    f"Connected to Plex server: {self.plex_server.friendlyName} (account: {account_name})"
                )
            except Exception as e:
                self.logger.warning(f"Could not verify Plex server connection: {e}")

            # Start AlertListener
            self.logger.info(f"Creating AlertListener for {self.server.name}")
            try:
                self.alert_listener = AlertListener(
                    server=self.plex_server,
                    callback=self._on_alert,
                    callbackError=self._on_alert_error,
                )
                self.logger.info("AlertListener created successfully")
            except Exception as e:
                self.logger.error(f"Failed to create AlertListener: {e}", exc_info=True)
                self._fallback_to_polling()
                return

            self.logger.info(f"Starting Plex AlertListener for {self.server.name}")
            try:
                self.alert_listener.start()
                self.logger.info(
                    "AlertListener started successfully - WebSocket connection should be active"
                )
            except Exception as e:
                self.logger.error(f"Failed to start AlertListener: {e}", exc_info=True)
                self._fallback_to_polling()
                return

            # Keep the listener running
            self.logger.info("Entering monitoring loop...")
            loop_count = 0
            while self.running and not self._stop_event.is_set():
                # Log periodic status
                loop_count += 1
                if loop_count % 6 == 1:  # Every minute (6 * 10 seconds)
                    self.logger.debug(
                        f"AlertListener monitoring active (events: {self.event_count}, errors: {self.error_count})"
                    )

                # Simple check - just wait and let the AlertListener handle reconnections
                self._stop_event.wait(10)

            self.logger.info("Exiting monitoring loop")

        except Exception as e:
            self.logger.error(f"Plex collector failed: {e}", exc_info=True)
            self.error_count += 1
            # Fallback to polling on any error
            self.logger.info("Falling back to polling due to error")
            self._fallback_to_polling()
        finally:
            if self.alert_listener:
                try:
                    self.logger.info("Stopping AlertListener...")
                    self.alert_listener.stop()
                    self.logger.info("AlertListener stopped")
                except Exception as e:
                    self.logger.error(f"Error stopping AlertListener: {e}")

    def stop(self):
        """Stop the Plex collector and AlertListener."""
        super().stop()
        if self.alert_listener:
            try:
                self.alert_listener.stop()
            except Exception as e:
                self.logger.error(f"Error stopping AlertListener: {e}")

        # Clean up session manager
        try:
            self.session_manager.cleanup_all_sessions()
        except Exception as e:
            self.logger.error(f"Error cleaning up session manager: {e}")

    def _on_alert(self, data: dict[str, Any]):
        """Handle Plex alert events."""
        try:
            alert_type = data.get("type")
            if alert_type in EXCLUDED_ALERT_TYPES:
                self.logger.debug(f"Skipping Plex alert type: {alert_type}")
                return

            self.logger.info(f"📡 Received Plex alert: {data}")

            # Use the enhanced session manager to process alerts
            success = self.session_manager.process_alert(data, self.server.id)
            if success:
                self.event_count += 1
            else:
                self.error_count += 1

        except Exception as e:
            self.logger.error(f"Error handling Plex alert: {e}", exc_info=True)
            self.error_count += 1

    def _on_alert_error(self, error):
        """Handle AlertListener errors."""
        self.logger.error(f"❌ Plex AlertListener error: {error}")
        self.error_count += 1

    def _handle_playing_alert(self, data: dict[str, Any]):
        """Handle playing state alerts from Plex."""
        playing_queue = data.get("PlayQueue", {})
        if not playing_queue:
            return

        session_key = playing_queue.get("playQueueSessionKey")
        if not session_key:
            return

        # Get session details from server
        try:
            if self.plex_server:
                sessions = self.plex_server.sessions()
                target_session = None

                for session in sessions:
                    if hasattr(session, "sessionKey") and str(
                        session.sessionKey
                    ) == str(session_key):
                        target_session = session
                        break

                if target_session:
                    self._process_session(target_session, "session_progress")

        except Exception as e:
            self.logger.error(f"Failed to get session details: {e}")

    def _handle_timeline_alert(self, data: dict[str, Any]):
        """Handle timeline alerts from Plex."""
        timeline_entries = data.get("TimelineEntry", [])
        if not isinstance(timeline_entries, list):
            timeline_entries = [timeline_entries]

        for entry in timeline_entries:
            if entry.get("type") == "video" or entry.get("type") == "music":
                state = entry.get("state")
                session_key = entry.get("sessionKey")

                if session_key and state:
                    self._handle_timeline_entry(entry, session_key, state)

    def _handle_timeline_entry(
        self, entry: dict[str, Any], session_key: str, state: str
    ):
        """Process a timeline entry."""
        try:
            # Get full session details
            if self.plex_server:
                sessions = self.plex_server.sessions()
                target_session = None

                for session in sessions:
                    if hasattr(session, "sessionKey") and str(
                        session.sessionKey
                    ) == str(session_key):
                        target_session = session
                        break

                if target_session:
                    event_type = self._map_plex_state_to_event(state)
                    if event_type:
                        self._process_session(target_session, event_type)

        except Exception as e:
            self.logger.error(f"Failed to handle timeline entry: {e}")

    def _process_session(self, session, event_type: str):
        """Process a Plex session into an ActivityEvent."""
        try:
            # Extract session data
            session_data = self._extract_session_data(session)
            if not session_data:
                return

            # Create activity event
            event = ActivityEvent(
                event_type=event_type,
                server_id=self.server.id,
                session_id=session_data["session_id"],
                user_name=session_data["user_name"],
                media_title=session_data["media_title"],
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
                client_name=session_data.get("client_name"),
                ip_address=session_data.get("ip_address"),
                platform=session_data.get("platform"),
                player_version=session_data.get("player_version"),
                state=session_data.get("state"),
                transcoding_info=session_data.get("transcoding_info"),
                metadata=session_data.get("metadata"),
                artwork_url=session_data.get("artwork_url"),
                thumbnail_url=session_data.get("thumbnail_url"),
            )

            self._emit_event(event)

        except Exception as e:
            self.logger.error(f"Failed to process Plex session: {e}", exc_info=True)

    def _extract_session_data(self, session) -> dict[str, Any] | None:
        """Extract relevant data from Plex session object."""
        try:
            # Basic session info
            session_id = str(getattr(session, "sessionKey", ""))
            if not session_id:
                return None

            # User info
            user_name = (
                getattr(session.user, "title", "Unknown")
                if hasattr(session, "user")
                else "Unknown"
            )
            user_id = (
                str(getattr(session.user, "id", ""))
                if hasattr(session, "user")
                else None
            )

            # Media info
            media = session
            media_title = getattr(media, "title", "Unknown")
            media_type = getattr(media, "type", "unknown")
            media_id = str(getattr(media, "ratingKey", ""))

            # Series info for TV shows
            series_name = None
            season_number = None
            episode_number = None
            if media_type == "episode":
                series_name = getattr(media, "grandparentTitle", None)
                season_number = getattr(media, "parentIndex", None)
                episode_number = getattr(media, "index", None)

            # Timing info
            duration_ms = (
                getattr(media, "duration", 0) if hasattr(media, "duration") else 0
            )
            view_offset = (
                getattr(session, "viewOffset", 0)
                if hasattr(session, "viewOffset")
                else 0
            )
            position_ms = view_offset

            # Player info
            player = getattr(session, "player", None)
            device_name = getattr(player, "title", "Unknown") if player else "Unknown"
            client_name = getattr(player, "product", "Unknown") if player else "Unknown"
            platform = getattr(player, "platform", "Unknown") if player else "Unknown"
            player_version = (
                getattr(player, "version", "Unknown") if player else "Unknown"
            )

            # Network info
            ip_address = getattr(player, "address", None) if player else None

            # State
            state = getattr(session, "state", "unknown")

            # Transcoding info
            transcoding_info = {}
            if hasattr(session, "transcodeSessions") and session.transcodeSessions:
                transcode = session.transcodeSessions[0]
                transcoding_info = {
                    "is_transcoding": True,
                    "video_codec": getattr(transcode, "videoCodec", None),
                    "audio_codec": getattr(transcode, "audioCodec", None),
                    "container": getattr(transcode, "container", None),
                    "video_resolution": getattr(transcode, "videoResolution", None),
                    "transcoding_speed": getattr(transcode, "speed", None),
                }
            else:
                # Check media streams for direct play info
                if hasattr(media, "media") and media.media:
                    media_item = media.media[0]
                    if hasattr(media_item, "parts") and media_item.parts:
                        part = media_item.parts[0]
                        transcoding_info = {
                            "is_transcoding": False,
                            "direct_play": True,
                            "container": getattr(part, "container", None),
                        }

            # Artwork
            artwork_url = None
            thumbnail_url = None
            if hasattr(media, "thumb") and self.plex_server:
                thumbnail_url = self.plex_server.url(media.thumb, includeToken=True)
            if hasattr(media, "art") and self.plex_server:
                artwork_url = self.plex_server.url(media.art, includeToken=True)

            return {
                "session_id": session_id,
                "user_name": user_name,
                "user_id": user_id,
                "media_title": media_title,
                "media_type": media_type,
                "media_id": media_id,
                "series_name": series_name,
                "season_number": season_number,
                "episode_number": episode_number,
                "duration_ms": duration_ms,
                "position_ms": position_ms,
                "device_name": device_name,
                "client_name": client_name,
                "ip_address": ip_address,
                "platform": platform,
                "player_version": player_version,
                "state": state,
                "transcoding_info": transcoding_info,
                "artwork_url": artwork_url,
                "thumbnail_url": thumbnail_url,
                "metadata": {
                    "plex_session_key": session_id,
                    "plex_rating_key": media_id,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to extract session data: {e}", exc_info=True)
            return None

    def _map_plex_state_to_event(self, plex_state: str) -> str | None:
        """Map Plex state to activity event type."""
        state_mapping = {
            "playing": "session_progress",
            "paused": "session_pause",
            "stopped": "session_end",
            "buffering": "session_progress",
        }
        return state_mapping.get(plex_state.lower())

    def _fallback_to_polling(self):
        """Fallback to polling if AlertListener is not available."""
        self.logger.info("Using polling fallback for Plex server")

        while self.running and not self._stop_event.is_set():
            try:
                client = self._get_media_client()
                if client:
                    sessions = client.now_playing()
                    self._process_polling_sessions(sessions)

                # Poll every 30 seconds
                self._stop_event.wait(30)

            except Exception as e:
                self.logger.error(f"Polling error: {e}")
                self._stop_event.wait(60)  # Wait longer on error

    def _process_polling_sessions(self, sessions):
        """Process sessions from polling."""
        for session_data in sessions:
            try:
                event = ActivityEvent(
                    event_type="session_progress",
                    server_id=self.server.id,
                    session_id=session_data.get("session_id", ""),
                    user_name=session_data.get("user_name", "Unknown"),
                    media_title=session_data.get("media_title", "Unknown"),
                    timestamp=datetime.now(UTC),
                    media_type=session_data.get("media_type"),
                    duration_ms=session_data.get("duration_ms"),
                    position_ms=session_data.get("position_ms"),
                    device_name=session_data.get("device_name"),
                    client_name=session_data.get("client"),
                    state=session_data.get("state", "playing"),
                )

                self._emit_event(event)

            except Exception as e:
                self.logger.error(f"Failed to process polling session: {e}")
