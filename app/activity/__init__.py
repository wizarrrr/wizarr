"""
Activity monitoring module for Wizarr.

Provides real-time activity monitoring and historical tracking of media playback
sessions across all configured media servers.
"""

from __future__ import annotations

import os

import structlog
from flask import Flask

from app.models import ActivitySession, ActivitySnapshot
from app.services.activity import ActivityService


def init_app(app: Flask) -> None:
    """Initialise activity monitoring features with the Flask application."""
    logger = structlog.get_logger(__name__)

    # Skip activity monitoring during tests
    if app.config.get("TESTING"):
        logger.debug("Skipping activity monitoring in test mode")
        return

    # Skip during migrations to avoid database locking and race conditions
    # This prevents session recovery from running during 'flask db upgrade'
    if os.environ.get("FLASK_SKIP_SCHEDULER") == "true":
        logger.debug("Skipping activity monitoring during migrations")
        return

    # Skip only in Werkzeug's reloader parent process (development mode)
    # WERKZEUG_RUN_MAIN is only set when using Flask's development server with reloader
    # In production (Gunicorn/uWSGI), this env var won't be set, so we should proceed
    if os.environ.get("WERKZEUG_RUN_MAIN") == "false":
        logger.debug("Skipping activity monitoring in reloader parent process")
        return

    from app.extensions import scheduler
    from app.tasks.activity import register_activity_tracking_reconcile_task

    from .tracking import reconcile_activity_tracking

    activity_scheduler = None
    if scheduler and hasattr(scheduler, "scheduler") and scheduler.scheduler:
        activity_scheduler = scheduler

    enabled = reconcile_activity_tracking(
        app,
        activity_scheduler,
        start_delay_seconds=2,
    )

    if activity_scheduler is not None:
        try:
            register_activity_tracking_reconcile_task(app, activity_scheduler)
        except Exception as exc:
            logger.warning(
                "Activity tracking setting checks are not scheduled",
                error=str(exc),
            )

    logger.info("Activity tracking initialized", enabled=enabled)


__all__ = ["ActivityService", "ActivitySession", "ActivitySnapshot", "init_app"]
