"""Manage the persistent activity tracking setting and monitor lifecycle."""

from __future__ import annotations

import threading

import structlog
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models import Settings

ACTIVITY_TRACKING_SETTING = "activity_tracking_enabled"
ACTIVITY_MONITOR_EXTENSION = "activity_monitor"
ACTIVITY_START_TIMER_EXTENSION = "activity_monitor_start_timer"

logger = structlog.get_logger(__name__)


def is_activity_tracking_enabled() -> bool:
    """Return the stored tracking state. Tracking is enabled by default."""
    try:
        setting = Settings.query.filter_by(key=ACTIVITY_TRACKING_SETTING).first()
    except (RuntimeError, SQLAlchemyError) as exc:
        logger.warning("activity_tracking_setting_load_failed", error=str(exc))
        return True

    if setting is None or setting.value is None:
        return True

    return str(setting.value).strip().lower() not in {"false", "0", "no", "off"}


def set_activity_tracking_enabled(enabled: bool) -> None:
    """Store the activity tracking state."""
    setting = Settings.query.filter_by(key=ACTIVITY_TRACKING_SETTING).first()
    value = "true" if enabled else "false"

    if setting is None:
        setting = Settings(key=ACTIVITY_TRACKING_SETTING, value=value)
        db.session.add(setting)
    else:
        setting.value = value

    db.session.commit()


def start_activity_tracking(app: Flask, delay_seconds: float = 0) -> None:
    """Create and start the activity monitor when it is not active."""
    from app.activity.monitoring.monitor import WebSocketMonitor

    monitor = app.extensions.get(ACTIVITY_MONITOR_EXTENSION)
    timer = app.extensions.get(ACTIVITY_START_TIMER_EXTENSION)

    if monitor is not None and (monitor.monitoring or timer is not None):
        return

    if monitor is None:
        monitor = WebSocketMonitor(app)
        app.extensions[ACTIVITY_MONITOR_EXTENSION] = monitor

    def start_monitor() -> None:
        app.extensions.pop(ACTIVITY_START_TIMER_EXTENSION, None)

        with app.app_context():
            if not is_activity_tracking_enabled():
                app.extensions.pop(ACTIVITY_MONITOR_EXTENSION, None)
                return

        try:
            from app.tasks.activity import recover_sessions_on_startup_task

            recovered_count = recover_sessions_on_startup_task(app)
            logger.info(
                "activity_session_recovery_completed",
                recovered_count=recovered_count,
            )
        except Exception as exc:
            logger.error(
                "activity_session_recovery_failed",
                error=str(exc),
                exc_info=True,
            )

        monitor.start_monitoring()

    if delay_seconds > 0:
        timer = threading.Timer(delay_seconds, start_monitor)
        timer.daemon = True
        app.extensions[ACTIVITY_START_TIMER_EXTENSION] = timer
        timer.start()
        return

    start_monitor()


def stop_activity_tracking(app: Flask) -> None:
    """Stop the activity monitor and cancel a pending start."""
    timer = app.extensions.pop(ACTIVITY_START_TIMER_EXTENSION, None)
    if timer is not None:
        timer.cancel()

    monitor = app.extensions.pop(ACTIVITY_MONITOR_EXTENSION, None)
    if monitor is not None:
        monitor.stop_monitoring()


def reconcile_activity_tracking(
    app: Flask,
    scheduler=None,
    *,
    start_delay_seconds: float = 0,
) -> bool:
    """Apply the stored tracking state to the monitor and scheduler."""
    from app.tasks.activity import (
        activity_tasks_registered,
        register_activity_tasks,
        unregister_activity_tasks,
    )

    with app.app_context():
        enabled = is_activity_tracking_enabled()

    if enabled:
        start_activity_tracking(app, delay_seconds=start_delay_seconds)
        if scheduler is not None and not activity_tasks_registered(scheduler):
            register_activity_tasks(app, scheduler)
    else:
        stop_activity_tracking(app)
        if scheduler is not None:
            unregister_activity_tasks(scheduler)

    return enabled
