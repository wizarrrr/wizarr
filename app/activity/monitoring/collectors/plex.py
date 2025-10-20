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
