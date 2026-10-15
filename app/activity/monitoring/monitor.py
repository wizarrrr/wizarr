"""
WebSocket monitoring infrastructure for Wizarr.

Manages real-time connections to media servers for activity monitoring
using WebSocket APIs where available, with fallback to polling.
"""

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime, timedelta
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

# Timeout (connect, read) in seconds for now-playing polls. A poll runs every
# 10-30 seconds, so a hung server must not block the collector for a minute.
POLL_TIMEOUT = (5, 20)

# Maximum time in seconds that stop_monitoring() waits for the collector
# threads. A collector in a slow poll stops after that poll. The threads are
# daemon threads, so a slow collector does not block the process exit.
COLLECTOR_JOIN_TIMEOUT = 30

# Maximum time in seconds that a monitor pass waits for the stopped collector
# of a server before it starts a new collector for that server. If the old
# thread does not stop in this time, the next pass tries again.
COLLECTOR_RESTART_JOIN_TIMEOUT = 10

# A failed poll keeps the active sessions, because most errors are short. When
# the polls of a collector fail for longer than this time, the collector ends
# its active sessions as if the server reported no sessions.
POLL_OUTAGE_LIMIT = timedelta(minutes=10)


class WebSocketMonitor:
    """Manages WebSocket connections to media servers for real-time activity monitoring."""

    def __init__(self, app: Flask):
        global _app_instance
        self.app = app
        _app_instance = app  # Store globally for background thread access
        self.logger = structlog.get_logger(__name__)
        self.activity_service = ActivityService()
        self.connections: dict[int, BaseCollector] = {}
        # Each collector loops until it stops, so it keeps its thread all the
        # time. A fixed-size pool gave no thread to the collectors after the
        # pool size. Thus each collector gets its own thread.
        self._monitor_thread: threading.Thread | None = None
        # The thread of each collector, by server id. The monitor keeps the
        # handle after the collector stops, until the thread ends. It does
        # not start a new collector for a server while the old thread runs.
        self._collector_threads: dict[int, threading.Thread] = {}
        self.monitoring = False
        self._stop_event = threading.Event()
        self._tables_ready = False

    def start_monitoring(self):
        """Start monitoring all configured servers."""
        if self.monitoring:
            self.logger.debug("Activity monitoring already started, skipping")
            return

        # Use a new stop event for each run. A loop of an earlier run that
        # did not stop yet keeps its own set event, and so it stops.
        self._stop_event = threading.Event()

        self.monitoring = True
        self.logger.info("Starting activity monitoring")

        # Start monitoring in background thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(self._stop_event,),
            name="activity-monitor",
            daemon=True,
        )
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stop all monitoring connections."""
        if not self.monitoring:
            return

        self.logger.info("Stopping activity monitoring")
        self.monitoring = False
        self._stop_event.set()

        # Wait for the monitor loop first. Then it cannot start a new
        # collector after the collectors stop. A pass of the loop reads the
        # database only, so the wait is short.
        monitor_thread, self._monitor_thread = self._monitor_thread, None
        if (
            monitor_thread is not None
            and monitor_thread is not threading.current_thread()
        ):
            monitor_thread.join()

        # Stop all collectors
        for collector in self.connections.values():
            try:
                collector.stop()
            except Exception as e:
                self.logger.error(f"Error stopping collector: {e}")

        self.connections.clear()

        deadline = time.monotonic() + COLLECTOR_JOIN_TIMEOUT
        for thread in self._collector_threads.values():
            thread.join(max(0.0, deadline - time.monotonic()))
        # Keep the handles of the threads that still run. A new start of the
        # monitor waits for them before it starts a collector for that server.
        self._collector_threads = {
            server_id: thread
            for server_id, thread in self._collector_threads.items()
            if thread.is_alive()
        }
        if self._collector_threads:
            names = ", ".join(t.name for t in self._collector_threads.values())
            self.logger.warning(
                f"Collectors did not stop in {COLLECTOR_JOIN_TIMEOUT} s: {names}"
            )

    def _monitor_loop(self, stop_event: threading.Event | None = None):
        """Main monitoring loop that manages collectors."""
        stop_event = stop_event or self._stop_event
        while self.monitoring and not stop_event.is_set():
            try:
                # Use a new app context (and so a new database session) for
                # each pass. A long-lived session keeps old MediaServer rows
                # in its identity map and does not see server edits.
                with self.app.app_context():
                    self._update_collectors()
                stop_event.wait(30)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                stop_event.wait(5)

    def _start_collector(self, server_id: int, collector: "BaseCollector") -> None:
        """Run the collector in its own daemon thread."""
        thread = threading.Thread(
            target=self._run_collector,
            args=(server_id, collector),
            name=f"activity-collector-{server_id}",
            daemon=True,
        )
        self._collector_threads[server_id] = thread
        thread.start()

    def _join_old_collector(self, server_id: int) -> bool:
        """Wait for the stopped collector thread of a server.

        Return True when no old collector thread runs for the server. Then the
        monitor can start a new collector. If the old thread does not stop in
        COLLECTOR_RESTART_JOIN_TIMEOUT, the monitor keeps its handle and tries
        again in the next pass.
        """
        thread = self._collector_threads.get(server_id)
        if thread is None:
            return True
        thread.join(COLLECTOR_RESTART_JOIN_TIMEOUT)
        if thread.is_alive():
            self.logger.warning(
                f"The old collector for server {server_id} did not stop in "
                f"{COLLECTOR_RESTART_JOIN_TIMEOUT} s, trying again in the next pass"
            )
            return False
        del self._collector_threads[server_id]
        return True

    def _run_collector(self, server_id: int, collector: "BaseCollector") -> None:
        try:
            collector.start()
        except Exception as e:
            self.logger.error(
                f"Collector for server {server_id} failed: {e}", exc_info=True
            )

    def _update_collectors(self):
        """Update collectors based on current server configuration."""
        if db is None:
            return

        try:
            if not self._tables_ready:
                # Check if the media_server table exists before querying
                from sqlalchemy import inspect

                inspector = inspect(db.engine)
                if "media_server" not in inspector.get_table_names():
                    # Tables not created yet (fresh install or tests)
                    return
                self._tables_ready = True

            # Get all active media servers. The collectors do not use the
            # import jobs, so do not load them on each pass.
            from sqlalchemy.orm import lazyload

            servers = (
                db.session.query(MediaServer)
                .options(lazyload(MediaServer.historical_import_jobs))
                .filter_by(verified=True)
                .all()
            )
            current_server_ids = {server.id for server in servers}
            active_collector_ids = set(self.connections.keys())

            # Remove collectors for deleted/disabled servers. The monitor keeps
            # the thread handle until the thread ends.
            for server_id in active_collector_ids - current_server_ids:
                collector = self.connections.pop(server_id)
                collector.stop()
                self.logger.info(f"Stopped monitoring server {server_id}")

            # Forget the threads of stopped collectors that ended.
            for server_id, thread in list(self._collector_threads.items()):
                if server_id not in self.connections and not thread.is_alive():
                    del self._collector_threads[server_id]

            # A changed server type needs a different collector class.
            for server in servers:
                collector = self.connections.get(server.id)
                if (
                    collector is not None
                    and getattr(collector.server, "server_type", None)
                    != server.server_type
                ):
                    self.connections.pop(server.id)
                    collector.stop()
                    self.logger.info(
                        f"Server {server.id} changed type, restarting its collector"
                    )

            # Add collectors for new servers
            for server in servers:
                if server.id not in self.connections:
                    # A stopped collector of this server can still run, for
                    # example in a slow poll. Do not start a second collector.
                    if not self._join_old_collector(server.id):
                        continue
                    self.logger.info(
                        f"Creating collector for server {server.id} ({server.server_type})"
                    )
                    collector = self._create_collector(server)
                    if collector:
                        self.connections[server.id] = collector
                        self._start_collector(server.id, collector)
                        self.logger.info(
                            f"Started monitoring server {server.id} ({server.server_type})"
                        )
                    else:
                        self.logger.error(
                            f"Failed to create collector for server {server.id}"
                        )
                else:
                    # Server already has a collector - check if it's still running
                    collector = self.connections[server.id]
                    # Give the collector the current row. The collector
                    # builds a new client when the URL or the key changed.
                    collector.update_server(server)
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
            collector_options = {
                "app": self.app,
                "batch_callback": self._on_activity_events,
            }

            if server.server_type == "plex":
                self.logger.info("Creating PollingCollector for Plex...")
                from .collectors.polling import PollingCollector

                collector = PollingCollector(
                    server, self._on_activity_event, **collector_options
                )
                self.logger.info(f"PollingCollector created for Plex: {collector}")
                return collector
            if server.server_type == "jellyfin":
                self.logger.info("Creating JellyfinCollector...")
                from .collectors.jellyfin import JellyfinCollector

                return JellyfinCollector(
                    server, self._on_activity_event, **collector_options
                )
            if server.server_type == "emby":
                self.logger.info("Creating EmbyCollector...")
                from .collectors.emby import EmbyCollector

                return EmbyCollector(
                    server, self._on_activity_event, **collector_options
                )
            if server.server_type == "audiobookshelf":
                self.logger.info("Creating AudiobookshelfCollector...")
                from .collectors.audiobookshelf import AudiobookshelfCollector

                return AudiobookshelfCollector(
                    server, self._on_activity_event, **collector_options
                )
            # For other server types, use polling collector
            self.logger.info("Creating PollingCollector...")
            from .collectors.polling import PollingCollector

            return PollingCollector(
                server, self._on_activity_event, **collector_options
            )

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

    def _on_activity_events(self, events: list[ActivityEvent]):
        """Handle all events of one poll cycle in one app context and transaction."""
        if not events:
            return
        try:
            with self.app.app_context():
                self.activity_service.record_activity_events(events)
            self.logger.debug(f"Recorded {len(events)} activity events")
        except Exception as e:
            self.logger.error(f"Failed to handle activity events: {e}", exc_info=True)

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
        self,
        server: MediaServer,
        event_callback: Callable[[ActivityEvent], None],
        *,
        app: Optional["Flask"] = None,
        batch_callback: Callable[[list[ActivityEvent]], None] | None = None,
    ):
        self.server = server
        self.event_callback = event_callback
        self.batch_callback = batch_callback
        self.app = app
        self.logger = structlog.get_logger(
            f"activity.collector.{getattr(server, 'server_type', 'unknown')}"
        )
        self.running = False
        self.last_event_time: datetime | None = None
        self.event_count = 0
        self.error_count = 0
        self._stop_event = threading.Event()
        self._client = None
        self._client_signature: tuple | None = None
        self._pending_events: list[ActivityEvent] | None = None
        # Time of the last poll that returned a session list.
        self.last_successful_poll: datetime | None = None
        self.consecutive_failed_polls = 0
        # When set, new events use this time and not the current time.
        self._event_time: datetime | None = None

    def start(self):
        """Start collecting activity data."""
        if self.running or self._stop_event.is_set():
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
        # Set the event also before the loop starts. Then a collector thread
        # that starts after stop() exits at once.
        self._stop_event.set()
        if not self.running:
            return

        self.logger.info(f"Stopping collector for {self.server.name}")
        self.running = False

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
        """Emit an activity event, or keep it for the current batch."""
        if self._pending_events is not None:
            self._pending_events.append(event)
            return

        try:
            self.event_callback(event)
            self.last_event_time = datetime.now(UTC)
            self.event_count += 1
        except Exception as e:
            self.logger.error(f"Failed to emit event: {e}")
            self.error_count += 1

    @contextmanager
    def _event_batch(self) -> Iterator[None]:
        """Collect the events of one poll cycle and send them together.

        The monitor records a batch in one app context and one transaction.
        Without a batch callback, the events go one by one as before.
        """
        if self._pending_events is not None:
            yield
            return

        self._pending_events = []
        try:
            yield
        finally:
            events, self._pending_events = self._pending_events, None
            self._send_batch(events)

    def _send_batch(self, events: list[ActivityEvent]) -> None:
        if not events:
            return

        if self.batch_callback is None:
            for event in events:
                self._emit_event(event)
            return

        try:
            self.batch_callback(events)
            self.last_event_time = datetime.now(UTC)
            self.event_count += len(events)
        except Exception as e:
            self.logger.error(f"Failed to emit events: {e}")
            self.error_count += 1

    @staticmethod
    def _server_signature(server) -> tuple:
        """Return the server values that a media client depends on."""
        return (
            getattr(server, "server_type", None),
            getattr(server, "url", None),
            getattr(server, "api_key", None),
        )

    def update_server(self, server: MediaServer) -> None:
        """Use a new copy of the server row. Rebuild the client when it changed."""
        if self._server_signature(server) != self._server_signature(self.server):
            self.logger.info(
                f"Server {getattr(server, 'id', '?')} settings changed, "
                "the collector builds a new client"
            )
            self._client = None
        self.server = server

    def _reset_media_client(self) -> None:
        """Drop the client so that the next poll builds a new one."""
        self._client = None

    def _get_media_client(self):
        """Get media client for this server.

        The collector keeps one client and builds a new one only when the
        server URL or credentials change, or after an error.
        """
        signature = self._server_signature(self.server)
        if self._client is not None and self._client_signature == signature:
            return self._client

        try:
            from app.services.media.service import get_client_for_media_server

            client = get_client_for_media_server(self.server)
            # REST clients read this attribute for each request.
            client.timeout = POLL_TIMEOUT
            self._client = client
            self._client_signature = signature
            return self._client
        except Exception as e:
            self.logger.error(f"Failed to get media client: {e}")
            self._client = None
            # Without a client the collector cannot poll. This is a failed poll.
            self._poll_failed()
            return None

    def _app_context(self):
        """Return an app context for media client calls that use the database."""
        if self.app is None:
            return nullcontext()
        return self.app.app_context()

    def _fetch_sessions(self, client) -> list[dict[str, Any]] | None:
        """Return the current sessions, or None when the poll failed.

        A failed poll does not end the active sessions. Only a successful
        empty result means that nothing plays. But when the polls fail for
        longer than POLL_OUTAGE_LIMIT, the collector ends its active sessions
        (see _poll_failed).
        """
        try:
            with self._app_context():
                sessions = client.now_playing()
        except Exception as e:
            self.logger.warning(
                f"Polling {getattr(self.server, 'name', 'server')} failed, "
                f"skipping this cycle: {e}"
            )
            self.error_count += 1
            self._reset_media_client()
            self._poll_failed()
            return None

        if sessions is None:
            self.logger.warning("Media server returned no session list, skipping cycle")
            self._poll_failed()
            return None

        self.last_successful_poll = datetime.now(UTC)
        self.consecutive_failed_polls = 0
        return list(sessions)

    def _event_now(self) -> datetime:
        """Return the time for a new event."""
        return self._event_time or datetime.now(UTC)

    def _has_active_sessions(self) -> bool:
        return bool(getattr(self, "active_sessions", None))

    def _process_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Compare the polled sessions with the known sessions and emit events."""
        raise NotImplementedError

    def _poll_failed(self) -> None:
        """Count a failed poll. After a long outage, end the active sessions.

        The sessions end at the time of the last successful poll, because the
        collector does not know what played after that time. When the server
        answers again, the next poll starts new sessions.
        """
        self.consecutive_failed_polls += 1
        last_success = self.last_successful_poll
        if last_success is None or not self._has_active_sessions():
            return

        outage = datetime.now(UTC) - last_success
        if outage < POLL_OUTAGE_LIMIT:
            return

        self.logger.warning(
            f"Polling {getattr(self.server, 'name', 'server')} failed for "
            f"{int(outage.total_seconds() // 60)} min "
            f"(failed polls: {self.consecutive_failed_polls}), ending its active sessions"
        )
        self._event_time = last_success
        try:
            with self._event_batch():
                self._process_sessions([])
        finally:
            self._event_time = None
