"""Helper utilities for activity blueprint routes."""

from typing import Any

import structlog
from flask import current_app, flash, redirect, render_template, request, url_for
from sqlalchemy.orm import joinedload

try:
    from flask_babel import gettext as _

    from app.extensions import db
    from app.models import (
        ActivitySession,
        ActivitySnapshot,
        HistoricalImportJob,
        MediaServer,
    )
except ImportError:
    MediaServer = None  # type: ignore[assignment]
    db = None  # type: ignore[assignment]
    HistoricalImportJob = None  # type: ignore[assignment]
    ActivitySession = None  # type: ignore[assignment]
    ActivitySnapshot = None  # type: ignore[assignment]

    def _(x):  # type: ignore[no-redef]
        return x


logger = structlog.get_logger(__name__)


def activity_settings_template() -> str:
    """Return template path for activity settings based on HX context."""
    return (
        "activity/settings_tab.html"
        if request.headers.get("HX-Request")
        else "activity/settings.html"
    )


def default_monitor_status() -> dict[str, object]:
    """Provide a fallback monitor status structure."""
    return {"monitoring_enabled": False, "connection_status": {}}


def load_monitor_status() -> dict[str, object]:
    """Return current activity monitor status."""
    monitor = getattr(current_app.extensions, "activity_monitor", None)
    return {
        "monitoring_enabled": monitor is not None,
        "connection_status": monitor.get_connection_status() if monitor else {},
    }


def load_verified_media_servers() -> list:
    """Return verified media servers available for historical import."""
    if MediaServer is None:
        return []

    try:
        return (
            MediaServer.query.filter_by(verified=True)
            .order_by(MediaServer.name.asc())
            .all()
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("media_servers_load_failed", error=str(exc))
        return []


def render_activity_settings(
    *,
    status: dict[str, object] | None = None,
    error: str | None = None,
    success: str | None = None,
    selected_server_id: int | None = None,
    selected_days_back: int | None = None,
):
    """Render the activity settings (full page or partial)."""
    template = activity_settings_template()

    if status is None:
        try:
            status = load_monitor_status()
        except Exception as exc:
            logger.error("settings_status_load_failed", error=str(exc))
            status = default_monitor_status()
            error = error or _("Failed to load settings")

    media_servers = load_verified_media_servers()
    if selected_days_back is None:
        selected_days_back = request.args.get("days_back", type=int, default=30)

    return render_template(
        template,
        status=status,
        media_servers=media_servers,
        error=error,
        success=success,
        selected_server_id=selected_server_id,
        selected_days_back=selected_days_back,
    )


def settings_action_response(
    *,
    success: str | None = None,
    error: str | None = None,
    selected_server_id: int | None = None,
    selected_days_back: int | None = None,
):
    """
    Return an appropriate response for activity settings actions.

    HTMX requests receive the re-rendered settings partial. Non-HTMX requests
    flash a message and redirect back to the settings page.
    """
    if request.headers.get("HX-Request"):
        return render_activity_settings(
            success=success,
            error=error,
            selected_server_id=selected_server_id,
            selected_days_back=selected_days_back,
        )

    if success:
        flash(success, "success")
    if error:
        flash(error, "error")

    extra_params: dict[str, Any] = {}
    if selected_days_back is not None:
        extra_params["days_back"] = selected_days_back
    return redirect(url_for("activity.activity_settings", **extra_params))


def render_historical_jobs_partial(server_id: int | None):
    """Render the historical import jobs partial."""
    if HistoricalImportJob is None:
        jobs: list = []
    else:
        query = HistoricalImportJob.query.options(
            joinedload(HistoricalImportJob.server)
        ).order_by(HistoricalImportJob.created_at.desc())

        if server_id:
            query = query.filter(HistoricalImportJob.server_id == server_id)

        jobs = query.limit(10).all()

    return render_template(
        "activity/_historical_jobs.html",
        jobs=jobs,
        selected_server_id=server_id,
    )


def delete_all_activity_data() -> int:
    """Remove all stored activity sessions and snapshots."""
    if db is None:
        raise RuntimeError("Database not initialised")

    try:
        deleted_snapshots = ActivitySnapshot.query.delete() if ActivitySnapshot else 0
        deleted_sessions = ActivitySession.query.delete() if ActivitySession else 0
        db.session.commit()
        return (deleted_snapshots or 0) + (deleted_sessions or 0)
    except Exception as exc:
        db.session.rollback()
        raise exc


def parse_int(form_key: str, default: int) -> int:
    """Parse an integer from request.form with graceful fallback."""
    try:
        value = request.form.get(form_key, default)
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def format_duration(value):
    """Format duration in hours to human-readable string."""
    if not value or value == 0:
        return "0 min"

    hours = int(value)
    minutes = int((value - hours) * 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours} hr")
    if minutes > 0:
        parts.append(f"{minutes} min")

    return " ".join(parts) or "0 min"
