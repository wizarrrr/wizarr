"""
Activity monitoring module for Wizarr.

Provides real-time activity monitoring and historical tracking of media playback
sessions across all configured media servers.
"""

from __future__ import annotations

import os
import threading

import structlog
from flask import Flask

from app.models import ActivitySession, ActivitySnapshot
from app.services.activity import ActivityService

from .monitoring.monitor import WebSocketMonitor


def init_app(app: Flask) -> None:
    """Initialise activity monitoring features with the Flask application."""
    logger = structlog.get_logger(__name__)

    # Skip activity monitoring during tests
    if app.config.get("TESTING"):
        logger.debug("Skipping activity monitoring in test mode")
        return

    # Skip only in Werkzeug's reloader parent process (development mode)
    # WERKZEUG_RUN_MAIN is only set when using Flask's development server with reloader
    # In production (Gunicorn/uWSGI), this env var won't be set, so we should proceed
    if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        logger.debug("Skipping activity monitoring in reloader parent process")
        return

    app.extensions = getattr(app, "extensions", {})
    if "activity_monitor" in app.extensions:
        logger.debug("Activity monitoring already initialized, skipping")
        return

    logger.info("Initializing activity monitoring")
    monitor = WebSocketMonitor(app)
    app.extensions["activity_monitor"] = monitor

    def delayed_start():
        import time

        time.sleep(2)

        try:
            from app.tasks.activity import recover_sessions_on_startup_task

            recovered_count = recover_sessions_on_startup_task(app)
            logger.info(
                "Session recovery completed on startup: %s orphaned sessions cleaned up",
                recovered_count,
            )
        except Exception as exc:
            logger.error("Session recovery failed on startup: %s", exc, exc_info=True)

        monitor.start_monitoring()

    threading.Thread(target=delayed_start, daemon=True).start()

    logger.info("Activity monitoring initialized")


__all__ = ["ActivitySession", "ActivitySnapshot", "ActivityService", "init_app"]
