"""
Emby activity collector using WebSocket API for real-time monitoring.

Connects to Emby's WebSocket endpoint to receive real-time notifications
about playback events. Uses similar approach to Jellyfin since Emby
and Jellyfin share similar APIs.
"""

import json
from datetime import UTC, datetime
from typing import Any

try:
    import websocket  # websocket-client package

    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

from ...domain.models import ActivityEvent
from ..monitor import BaseCollector


class EmbyCollector(BaseCollector):
    """Emby activity collector using WebSocket for real-time events."""

    def __init__(self, server, event_callback):
        super().__init__(server, event_callback)
        self.ws: websocket.WebSocketApp | None = None
        self.authenticated = False
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self.last_ping = datetime.now(UTC)

    def _collect_loop(self):
        """Main collection loop using Emby WebSocket."""
        if not WEBSOCKET_AVAILABLE:
            self.logger.error("websocket-client not available, falling back to polling")
            self._fallback_to_polling()
            return

        retry_count = 0
        max_retries = 5

        while (
            self.running and not self._stop_event.is_set() and retry_count < max_retries
        ):
            try:
                self._connect_websocket()
                retry_count = 0  # Reset on successful connection

                # Keep connection alive
                while self.running and not self._stop_event.is_set():
                    if self.ws and not self.ws.sock:
                        self.logger.warning("WebSocket connection lost, reconnecting")
                        break

                    # Send ping periodically
                    if (datetime.now(UTC) - self.last_ping).total_seconds() > 30:
                        self._send_ping()
                        self.last_ping = datetime.now(UTC)

                    self._stop_event.wait(5)

            except Exception as e:
                retry_count += 1
                self.logger.error(
                    f"Emby WebSocket error: {e}, retry {retry_count}/{max_retries}"
                )
                self.error_count += 1

                if retry_count < max_retries:
                    wait_time = min(60, 5 * retry_count)  # Exponential backoff, max 60s
                    self._stop_event.wait(wait_time)

        if retry_count >= max_retries:
            self.logger.error("Max retries reached, falling back to polling")
            self._fallback_to_polling()

    def _connect_websocket(self):
        """Connect to Emby WebSocket endpoint."""
        try:
            # Build WebSocket URL - Emby uses similar format to Jellyfin
            base_url = self.server.server_url.rstrip("/")
            ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url += f"/embywebsocket?api_key={self.server.server_api_key}"

            self.logger.info(f"Connecting to Emby WebSocket: {ws_url}")

            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )

            # Run WebSocket in this thread
            self.ws.run_forever(ping_interval=30, ping_timeout=10)

        except Exception as e:
            self.logger.error(f"Failed to connect to Emby WebSocket: {e}")
            raise

    def _on_open(self, ws):
        """Handle WebSocket connection opened."""
        self.logger.info(f"Connected to Emby WebSocket for {self.server.server_name}")

        # Subscribe to session events
        self._subscribe_to_sessions()

    def _on_message(self, ws, message):
        """Handle WebSocket message."""
        try:
            data = json.loads(message)
            message_type = data.get("MessageType")

            if message_type == "Sessions":
                self._handle_sessions_message(data)
            elif message_type == "PlaybackStart":
                self._handle_playback_start(data)
            elif message_type == "PlaybackProgress":
                self._handle_playback_progress(data)
            elif message_type == "PlaybackStopped":
                self._handle_playback_stopped(data)
            else:
                self.logger.debug(f"Ignoring message type: {message_type}")

        except Exception as e:
            self.logger.error(
                f"Error handling Emby WebSocket message: {e}", exc_info=True
            )
            self.error_count += 1

    def _on_error(self, ws, error):
        """Handle WebSocket error."""
        self.logger.error(f"Emby WebSocket error: {error}")
        self.error_count += 1

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed."""
        self.logger.info(f"Emby WebSocket closed: {close_status_code} - {close_msg}")

    def _subscribe_to_sessions(self):
        """Subscribe to session events."""
        try:
            subscribe_message = {
                "MessageType": "SessionsStart",
                "Data": "100,100",  # Request session updates every 100ms
            }

            if self.ws and self.ws.sock:
                self.ws.send(json.dumps(subscribe_message))
                self.logger.debug("Subscribed to Emby session events")

        except Exception as e:
            self.logger.error(f"Failed to subscribe to sessions: {e}")

    def _send_ping(self):
        """Send ping to keep connection alive."""
        try:
            if self.ws and self.ws.sock:
                ping_message = {"MessageType": "KeepAlive"}
                self.ws.send(json.dumps(ping_message))

        except Exception as e:
            self.logger.error(f"Failed to send ping: {e}")

    def _handle_sessions_message(self, data):
        """Handle Sessions message with current session data."""
        try:
            sessions_data = data.get("Data", [])
            if not isinstance(sessions_data, list):
                return

            current_session_ids = set()

            for session_data in sessions_data:
                session_id = session_data.get("Id")
                if not session_id:
                    continue

                current_session_ids.add(session_id)

                # Check if this is a new session or has significant changes
                if session_id not in self.active_sessions:
                    # New session
                    self.active_sessions[session_id] = session_data
                    if session_data.get("NowPlayingItem"):
                        self._emit_session_event(session_data, "session_start")
                else:
                    # Check for significant changes
                    old_session = self.active_sessions[session_id]
                    self.active_sessions[session_id] = session_data

                    # Check for state changes
                    old_state = old_session.get("PlayState", {}).get("IsPaused", False)
                    new_state = session_data.get("PlayState", {}).get("IsPaused", False)

                    if old_state != new_state:
                        if new_state:
                            self._emit_session_event(session_data, "session_pause")
                        else:
                            self._emit_session_event(session_data, "session_resume")
                    else:
                        # Regular progress update
                        self._emit_session_event(session_data, "session_progress")

            # Remove ended sessions
            ended_sessions = set(self.active_sessions.keys()) - current_session_ids
            for session_id in ended_sessions:
                old_session = self.active_sessions.pop(session_id)
                self._emit_session_event(old_session, "session_end")

        except Exception as e:
            self.logger.error(f"Error handling sessions message: {e}", exc_info=True)

    def _handle_playback_start(self, data):
        """Handle PlaybackStart message."""
        try:
            session_data = data.get("Data", {})
            session_id = session_data.get("SessionId")

            if session_id:
                self.active_sessions[session_id] = session_data
                self._emit_session_event(session_data, "session_start")

        except Exception as e:
            self.logger.error(f"Error handling playback start: {e}")

    def _handle_playback_progress(self, data):
        """Handle PlaybackProgress message."""
        try:
            session_data = data.get("Data", {})
            session_id = session_data.get("SessionId")

            if session_id:
                self.active_sessions[session_id] = session_data
                self._emit_session_event(session_data, "session_progress")

        except Exception as e:
            self.logger.error(f"Error handling playback progress: {e}")

    def _handle_playback_stopped(self, data):
        """Handle PlaybackStopped message."""
        try:
            session_data = data.get("Data", {})
            session_id = session_data.get("SessionId")

            if session_id and session_id in self.active_sessions:
                session_data = self.active_sessions.pop(session_id)
                self._emit_session_event(session_data, "session_end")

        except Exception as e:
            self.logger.error(f"Error handling playback stopped: {e}")

    def _emit_session_event(self, session_data: dict[str, Any], event_type: str):
        """Convert Emby session data to ActivityEvent and emit."""
        try:
            extracted_data = self._extract_session_data(session_data)
            if not extracted_data:
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
                season_number=extracted_data.get("season_number"),
                episode_number=extracted_data.get("episode_number"),
                duration_ms=extracted_data.get("duration_ms"),
                position_ms=extracted_data.get("position_ms"),
                device_name=extracted_data.get("device_name"),
                client_name=extracted_data.get("client_name"),
                ip_address=extracted_data.get("ip_address"),
                platform=extracted_data.get("platform"),
                player_version=extracted_data.get("player_version"),
                state=extracted_data.get("state"),
                transcoding_info=extracted_data.get("transcoding_info"),
                metadata=extracted_data.get("metadata"),
                artwork_url=extracted_data.get("artwork_url"),
                thumbnail_url=extracted_data.get("thumbnail_url"),
            )

            self._emit_event(event)

        except Exception as e:
            self.logger.error(f"Failed to emit Emby session event: {e}", exc_info=True)

    def _extract_session_data(
        self, session_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Extract relevant data from Emby session."""
        try:
            session_id = session_data.get("Id")
            if not session_id:
                return None

            # User info
            user_info = session_data.get("UserName", "Unknown")
            user_id = session_data.get("UserId")

            # Now playing item
            now_playing = session_data.get("NowPlayingItem", {})
            if not now_playing:
                return None

            media_title = now_playing.get("Name", "Unknown")
            media_type = now_playing.get("Type", "unknown").lower()
            media_id = now_playing.get("Id")

            # Series info for episodes
            series_name = None
            season_number = None
            episode_number = None
            if media_type == "episode":
                series_name = now_playing.get("SeriesName")
                season_number = now_playing.get("ParentIndexNumber")
                episode_number = now_playing.get("IndexNumber")

            # Timing info
            play_state = session_data.get("PlayState", {})
            duration_ms = (
                now_playing.get("RunTimeTicks", 0) // 10000
            )  # Convert from ticks
            position_ms = play_state.get("PositionTicks", 0) // 10000

            # Device info
            device_name = session_data.get("DeviceName", "Unknown")
            client_name = session_data.get("Client", "Unknown")
            app_version = session_data.get("ApplicationVersion")

            # Network info
            ip_address = session_data.get("RemoteEndPoint")

            # State
            is_paused = play_state.get("IsPaused", False)
            state = "paused" if is_paused else "playing"

            # Transcoding info - Emby structure might be slightly different
            transcoding_info = {}
            transcode_info = session_data.get("TranscodingInfo")
            if transcode_info:
                transcoding_info = {
                    "is_transcoding": True,
                    "video_codec": transcode_info.get("VideoCodec"),
                    "audio_codec": transcode_info.get("AudioCodec"),
                    "container": transcode_info.get("Container"),
                    "video_resolution": f"{transcode_info.get('Width', 0)}x{transcode_info.get('Height', 0)}",
                    "transcoding_speed": transcode_info.get("TranscodingSpeed"),
                }
            else:
                # Check if direct playing
                play_method = play_state.get("PlayMethod")
                transcoding_info = {
                    "is_transcoding": False,
                    "direct_play": play_method == "DirectPlay",
                    "direct_stream": play_method == "DirectStream",
                }

            # Artwork - Emby uses similar image system to Jellyfin
            artwork_url = None
            thumbnail_url = None
            if now_playing.get("ImageTags", {}).get("Primary"):
                base_url = self.server.server_url.rstrip("/")
                item_id = now_playing.get("Id")
                artwork_url = f"{base_url}/emby/Items/{item_id}/Images/Primary"
                thumbnail_url = f"{base_url}/emby/Items/{item_id}/Images/Primary?maxHeight=300&maxWidth=300"

            return {
                "session_id": session_id,
                "user_name": user_info,
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
                "platform": session_data.get("DeviceType"),
                "player_version": app_version,
                "state": state,
                "transcoding_info": transcoding_info,
                "artwork_url": artwork_url,
                "thumbnail_url": thumbnail_url,
                "metadata": {
                    "emby_session_id": session_id,
                    "emby_item_id": media_id,
                    "play_method": play_state.get("PlayMethod"),
                },
            }

        except Exception as e:
            self.logger.error(
                f"Failed to extract Emby session data: {e}", exc_info=True
            )
            return None

    def _fallback_to_polling(self):
        """Fallback to polling if WebSocket is not available."""
        self.logger.info("Using polling fallback for Emby server")

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

    def stop(self):
        """Stop the Emby collector and WebSocket connection."""
        super().stop()
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                self.logger.error(f"Error closing WebSocket: {e}")
