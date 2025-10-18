"""
WebSocket monitoring infrastructure for Wizarr.

Manages real-time connections to media servers for activity monitoring
using WebSocket APIs where available, with fallback to polling.
"""

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, Optional

import structlog

try:
    from flask import Flask

    from app.extensions import db
    from app.models import MediaServer
except ImportError:  # pragma: no cover
    Flask = None  # type: ignore
    MediaServer = None  # type: ignore
    db = None  # type: ignore

from app.activity.domain.models import ActivityEvent
from app.services.activity import ActivityService

# Global app instance for background thread access
_app_instance = None


class WebSocketMonitor:
    """Manages WebSocket connections to media servers for real-time activity monitoring."""

    def __init__(self, app: Flask):
        global _app_instance
        self.app = app
        _app_instance = app  # Store globally for background thread access
        self.logger = structlog.get_logger(__name__)
        self.activity_service = ActivityService()
        self.connections: dict[int, BaseCollector] = {}
        self.executor = None  # Initialize later when actually needed
        self.monitoring = False
        self._stop_event = threading.Event()

    def start_monitoring(self):
        """Start monitoring all configured servers."""
        if self.monitoring:
            self.logger.debug("Activity monitoring already started, skipping")
            return

        # Clear any previous stop signal before starting fresh
        self._stop_event.clear()

        self.monitoring = True
        self.logger.info("Starting activity monitoring")

        # Initialize executor if not already done
        if self.executor is None:
            self.executor = ThreadPoolExecutor(
                max_workers=10, thread_name_prefix="activity-monitor"
            )
            self.logger.info("Initialized ThreadPoolExecutor for activity monitoring")

        # Start monitoring in background thread
        self.executor.submit(self._monitor_loop)

    def stop_monitoring(self):
        """Stop all monitoring connections."""
        if not self.monitoring:
            return

        self.logger.info("Stopping activity monitoring")
        self.monitoring = False
        self._stop_event.set()

        # Stop all collectors
        for collector in self.connections.values():
            try:
                collector.stop()
            except Exception as e:
                self.logger.error(f"Error stopping collector: {e}")

        self.connections.clear()
        if self.executor:
            self.executor.shutdown(wait=True)
            self.executor = None

    def _monitor_loop(self):
        """Main monitoring loop that manages collectors."""
        with self.app.app_context():
            while self.monitoring and not self._stop_event.is_set():
                try:
                    self._update_collectors()
                    time.sleep(30)  # Check for new/removed servers every 30 seconds
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                    time.sleep(5)

    def _update_collectors(self):
        """Update collectors based on current server configuration."""
        if db is None:
            return

        try:
            # Check if the media_server table exists before querying
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            if "media_server" not in inspector.get_table_names():
                # Tables not created yet (fresh install or tests)
                return

            # Get all active media servers
            servers = db.session.query(MediaServer).filter_by(verified=True).all()
            current_server_ids = {server.id for server in servers}
            active_collector_ids = set(self.connections.keys())

            # Remove collectors for deleted/disabled servers
            for server_id in active_collector_ids - current_server_ids:
                collector = self.connections.pop(server_id)
                collector.stop()
                self.logger.info(f"Stopped monitoring server {server_id}")

            # Add collectors for new servers
            for server in servers:
                if server.id not in self.connections:
                    self.logger.info(
                        f"Creating collector for server {server.id} ({server.server_type})"
                    )
                    collector = self._create_collector(server)
                    if collector:
                        self.connections[server.id] = collector
                        self.logger.info(
                            f"Submitting collector task for server {server.id}"
                        )
                        if self.executor:
                            future = self.executor.submit(collector.start)
                            self.logger.info(
                                f"Started monitoring server {server.id} ({server.server_type})"
                            )

                            # Add a callback to catch any exceptions from the collector
                            def collector_done_callback(fut, server_id=server.id):
                                try:
                                    fut.result()  # This will raise any exceptions that occurred
                                except Exception as e:
                                    self.logger.error(
                                        f"Collector for server {server_id} failed: {e}",
                                        exc_info=True,
                                    )

                            future.add_done_callback(collector_done_callback)
                        else:
                            self.logger.error(
                                "Executor not initialized - cannot start collector"
                            )
                            continue
                    else:
                        self.logger.error(
                            f"Failed to create collector for server {server.id}"
                        )
                else:
                    # Server already has a collector - check if it's still running
                    collector = self.connections[server.id]
                    if not collector.is_connected():
                        self.logger.warning(
                            f"Collector for server {server.id} appears disconnected, checking status"
                        )
                        # Could add reconnection logic here if needed

        except Exception as e:
            # Silently ignore database errors during testing or when tables don't exist yet
            from sqlalchemy.exc import OperationalError

            if isinstance(e, OperationalError) and "no such table" in str(e):
                self.logger.debug(f"Database not fully initialized yet: {e}")
            else:
                self.logger.error(f"Failed to update collectors: {e}", exc_info=True)

    def _create_collector(self, server: MediaServer) -> Optional["BaseCollector"]:
        """Create appropriate collector for server type."""
        try:
            self.logger.info(
                f"Creating collector for server type: {server.server_type}"
            )

            if server.server_type == "plex":
                self.logger.info("Creating PlexCollector...")
                from .collectors.plex import PlexCollector

                collector = PlexCollector(server, self._on_activity_event)
                self.logger.info(f"PlexCollector created: {collector}")
                return collector
            if server.server_type == "jellyfin":
                self.logger.info("Creating JellyfinCollector...")
                from .collectors.jellyfin import JellyfinCollector

                return JellyfinCollector(server, self._on_activity_event)
            if server.server_type == "emby":
                self.logger.info("Creating EmbyCollector...")
                from .collectors.emby import EmbyCollector

                return EmbyCollector(server, self._on_activity_event)
            if server.server_type == "audiobookshelf":
                self.logger.info("Creating AudiobookshelfCollector...")
                from .collectors.audiobookshelf import AudiobookshelfCollector

                return AudiobookshelfCollector(server, self._on_activity_event)
            # For other server types, use polling collector
            self.logger.info("Creating PollingCollector...")
            from .collectors.polling import PollingCollector

            return PollingCollector(server, self._on_activity_event)

        except Exception as e:
            self.logger.error(
                f"Failed to create collector for server {server.id}: {e}", exc_info=True
            )
            return None

    def _on_activity_event(self, event: ActivityEvent):
        """Handle activity events from collectors."""
        try:
            with self.app.app_context():
                session = self.activity_service.record_activity_event(event)
                if session:
                    self.logger.debug(
                        f"Recorded activity event: {event.event_type} for {event.user_name}"
                    )
        except Exception as e:
            self.logger.error(f"Failed to handle activity event: {e}", exc_info=True)

    def get_connection_status(self) -> dict[int, dict[str, Any]]:
        """Get status of all monitoring connections."""
        status = {}
        for server_id, collector in self.connections.items():
            status[server_id] = {
                "connected": collector.is_connected(),
                "last_event": collector.get_last_event_time(),
                "event_count": collector.get_event_count(),
                "errors": collector.get_error_count(),
            }
        return status


class BaseCollector:
    """Base class for activity collectors."""

    def __init__(
        self, server: MediaServer, event_callback: Callable[[ActivityEvent], None]
    ):
        self.server = server
        self.event_callback = event_callback
        self.logger = structlog.get_logger(
            f"activity.collector.{getattr(server, 'server_type', 'unknown')}"
        )
        self.running = False
        self.last_event_time: datetime | None = None
        self.event_count = 0
        self.error_count = 0
        self._stop_event = threading.Event()

    def start(self):
        """Start collecting activity data."""
        if self.running:
            return

        self.running = True
        self.logger.info(f"Starting collector for {self.server.name}")
        try:
            self._collect_loop()
        except Exception as e:
            self.logger.error(
                f"Collector failed for {self.server.name}: {e}", exc_info=True
            )
            self.error_count += 1
        finally:
            self.running = False

    def stop(self):
        """Stop collecting activity data."""
        if not self.running:
            return

        self.logger.info(f"Stopping collector for {self.server.name}")
        self.running = False
        self._stop_event.set()

    def _collect_loop(self):
        """Main collection loop - to be implemented by subclasses."""
        raise NotImplementedError

    def is_connected(self) -> bool:
        """Check if collector is connected and working."""
        return self.running and not self._stop_event.is_set()

    def get_last_event_time(self) -> datetime | None:
        """Get timestamp of last event."""
        return self.last_event_time

    def get_event_count(self) -> int:
        """Get total event count."""
        return self.event_count

    def get_error_count(self) -> int:
        """Get total error count."""
        return self.error_count

    def _emit_event(self, event: ActivityEvent):
        """Emit an activity event."""
        try:
            self.event_callback(event)
            self.last_event_time = datetime.now(UTC)
            self.event_count += 1
        except Exception as e:
            self.logger.error(f"Failed to emit event: {e}")
            self.error_count += 1

    def _get_media_client(self):
        """Get media client for this server."""
        try:
            from app.services.media.service import get_client_for_media_server

            return get_client_for_media_server(self.server)
        except Exception as e:
            self.logger.error(f"Failed to get media client: {e}")
            return None
