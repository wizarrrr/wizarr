"""
Activity monitoring blueprint for Wizarr.

Provides routes for activity dashboard, analytics, and API endpoints
for managing and viewing media playback activity data.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy.orm import joinedload

try:
    from flask_babel import gettext as _

    from app.extensions import db
    from app.models import HistoricalImportJob, MediaServer
except ImportError:
    # For testing without Flask app context
    MediaServer = None  # type: ignore[assignment]
    db = None  # type: ignore[assignment]
    HistoricalImportJob = None  # type: ignore[assignment]

    def _(x):  # type: ignore[no-redef]
        return x


from app.activity.domain.models import ActivityQuery
from app.models import ActivitySession, ActivitySnapshot
from app.services.activity import ActivityService
from app.services.historical import HistoricalDataService

# Create blueprint
activity_bp = Blueprint(
    "activity",
    __name__,
    url_prefix="/activity",
    template_folder="../templates",
)


# Helper utilities ---------------------------------------------------------


def _activity_settings_template() -> str:
    """Return template path for activity settings based on HX context."""
    return (
        "activity/settings_tab.html"
        if request.headers.get("HX-Request")
        else "activity/settings.html"
    )


def _default_monitor_status() -> dict[str, object]:
    """Provide a fallback monitor status structure."""
    return {"monitoring_enabled": False, "connection_status": {}}


def _load_monitor_status() -> dict[str, object]:
    """Return current activity monitor status."""
    monitor = getattr(current_app.extensions, "activity_monitor", None)
    return {
        "monitoring_enabled": monitor is not None,
        "connection_status": monitor.get_connection_status() if monitor else {},
    }


def _load_verified_media_servers() -> list:
    """Return verified media servers available for historical import."""
    if MediaServer is None:
        return []

    try:
        return (
            MediaServer.query.filter_by(verified=True)
            .order_by(MediaServer.name.asc())
            .all()
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        structlog.get_logger(__name__).warning(
            "Failed to load media servers: %s", exc, exc_info=True
        )
        return []


def _render_activity_settings(
    *,
    status: dict[str, object] | None = None,
    error: str | None = None,
    success: str | None = None,
    selected_server_id: int | None = None,
    selected_days_back: int | None = None,
):
    """Render the activity settings (full page or partial)."""
    template = _activity_settings_template()
    logger = structlog.get_logger(__name__)

    if status is None:
        try:
            status = _load_monitor_status()
        except Exception as exc:
            logger.error(
                "Failed to load activity settings status: %s", exc, exc_info=True
            )
            status = _default_monitor_status()
            error = error or _("Failed to load settings")

    media_servers = _load_verified_media_servers()
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


def _settings_action_response(
    *,
    success: str | None = None,
    error: str | None = None,
    selected_server_id: int | None = None,
    selected_days_back: int | None = None,
):
    """
    Return an appropriate response for activity settings actions.

    HTMX requests receive the re-rendered settings partial. Non-HTMX requests
    flash a message and redirect back to the settings page to avoid duplicate
    submissions.
    """
    if request.headers.get("HX-Request"):
        return _render_activity_settings(
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


def _render_historical_jobs_partial(server_id: int | None):
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


def _delete_all_activity_data() -> int:
    """Remove all stored activity sessions and snapshots."""
    if db is None:
        raise RuntimeError("Database not initialised")

    try:
        deleted_snapshots = ActivitySnapshot.query.delete()
        deleted_sessions = ActivitySession.query.delete()
        db.session.commit()
        return (deleted_snapshots or 0) + (deleted_sessions or 0)
    except Exception as exc:
        db.session.rollback()
        raise exc


def _parse_int(form_key: str, default: int) -> int:
    """Parse an integer from request.form with graceful fallback."""
    try:
        value = request.form.get(form_key, default)
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


# Template filters
@activity_bp.app_template_filter("format_duration")
def format_duration_filter(value):
    """Format duration in hours to human-readable string."""
    if not value or value == 0:
        return "0m"

    hours = int(value)
    minutes = int((value - hours) * 60)

    if hours > 0:
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    return f"{minutes}m"


@activity_bp.route("/", methods=["GET"], strict_slashes=False)
@login_required
def activity_dashboard():
    """Display activity index with tabbed interface."""
    return render_template("activity/index.html")


@activity_bp.route("/dashboard")
@login_required
def dashboard_tab():
    """Display dashboard tab with statistics."""
    try:
        activity_service = ActivityService()

        # Get query parameters
        days = int(request.args.get("days", 7))

        # Get enhanced activity statistics
        stats = activity_service.get_dashboard_stats(days=days)

        return render_template("activity/dashboard_tab.html", stats=stats, days=days)

    except Exception as e:
        logger = structlog.get_logger(__name__)
        logger.error("Failed to load dashboard: %s", e, exc_info=True)
        return render_template(
            "activity/dashboard_tab.html",
            error=_("Failed to load dashboard data"),
            stats={},
            days=7,
        )


@activity_bp.route("/history")
@login_required
def history_tab():
    """Display history tab with activity table."""
    try:
        # Get available servers for filtering
        servers = []
        if db is not None:
            servers = db.session.query(MediaServer).filter_by(verified=True).all()

        return render_template("activity/history_tab.html", servers=servers)

    except Exception as e:
        logger = structlog.get_logger(__name__)
        logger.error("Failed to load history tab: %s", e, exc_info=True)
        return render_template(
            "activity/history_tab.html",
            error=_("Failed to load history data"),
            servers=[],
        )


@activity_bp.route("/grid")
@login_required
def activity_grid():
    """Get activity grid data."""
    try:
        activity_service = ActivityService()

        # Get query parameters
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))  # Table view - fewer rows per page
        days = request.args.get(
            "days", type=int
        )  # None if not provided - shows all data
        server_id = request.args.get("server_id", type=int)
        user_name = request.args.get("user_name")
        media_type = request.args.get("media_type")

        # Calculate offset
        offset = (page - 1) * limit

        # Build query
        if days is None or days == 0:
            # All time - no date filter (default for history tab)
            start_date = None
        else:
            # Apply date filter (for dashboard tab)
            start_date = datetime.now(UTC) - timedelta(days=days)

        query = ActivityQuery(
            server_ids=[server_id] if server_id else None,
            user_names=[user_name] if user_name else None,
            media_types=[media_type] if media_type else None,
            start_date=start_date,
            limit=limit,
            offset=offset,
            order_by="started_at",
            order_direction="desc",
        )

        sessions, total_count = activity_service.get_activity_sessions(query)

        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1

        return render_template(
            "activity/_activity_table.html",
            sessions=sessions,
            page=page,
            has_next=has_next,
            has_prev=has_prev,
            total_count=total_count,
            total_pages=total_pages,
        )

    except Exception as e:
        logger = structlog.get_logger(__name__)
        logger.error("Failed to load activity grid: %s", e, exc_info=True)
        return render_template(
            "activity/_activity_table.html",
            sessions=[],
            error=_("Failed to load activity data"),
        )


@activity_bp.route("/stats")
@login_required
def activity_stats():
    """Get activity statistics."""
    try:
        activity_service = ActivityService()
        days = int(request.args.get("days", 7))

        stats = activity_service.get_activity_stats(days=days)
        return jsonify(stats)

    except Exception as e:
        logger = structlog.get_logger(__name__)
        logger.error("Failed to get activity stats: %s", e, exc_info=True)
        return jsonify({"error": _("Failed to get activity statistics")}), 500


@activity_bp.route("/session/<int:session_id>")
@login_required
def activity_session(session_id):
    """Get session details."""
    try:
        if db is None:
            return jsonify({"error": _("Database not available")}), 500

        session = db.session.query(ActivitySession).get_or_404(session_id)

        return jsonify(session.to_dict())

    except Exception as e:
        logger = structlog.get_logger(__name__)
        logger.error(
            "Failed to get session %s: %s",
            session_id,
            e,
            exc_info=True,
        )
        return jsonify({"error": _("Failed to get session details")}), 500


@activity_bp.route("/export")
@login_required
def activity_export():
    """Export activity data as CSV or JSON."""
    try:
        activity_service = ActivityService()

        # Get query parameters
        format_type = request.args.get("format", "csv").lower()
        days = int(request.args.get("days", 30))
        server_id = request.args.get("server_id", type=int)
        user_name = request.args.get("user_name")

        # Build query
        query = ActivityQuery(
            server_ids=[server_id] if server_id else None,
            user_names=[user_name] if user_name else None,
            start_date=datetime.now(UTC) - timedelta(days=days),
            order_by="started_at",
            order_direction="desc",
        )

        sessions, _ = activity_service.get_activity_sessions(query)

        if format_type == "json":
            return jsonify([session.to_dict() for session in sessions])
        # CSV export
        import csv
        import io

        from flask import Response

        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        writer.writerow(
            [
                "Session ID",
                "User Name",
                "Media Title",
                "Media Type",
                "Started At",
                "Duration (minutes)",
                "Device Name",
                "Client Name",
                "Server ID",
            ]
        )

        # Write data
        for session in sessions:
            writer.writerow(
                [
                    session.session_id,
                    session.user_name,
                    session.media_title,
                    session.media_type,
                    session.started_at.isoformat() if session.started_at else "",
                    session.duration_minutes,
                    session.device_name,
                    session.client_name,
                    session.server_id,
                ]
            )

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=activity_export_{days}days.csv"
            },
        )

    except Exception as e:
        logger = structlog.get_logger(__name__)
        logger.error("Failed to export activity data: %s", e, exc_info=True)
        return (
            jsonify({"error": _("Failed to export activity data")}),  # type: ignore[misc]
            500,
        )


@activity_bp.route("/settings", methods=["GET", "POST"])
@login_required
def activity_settings():
    """Activity monitoring settings."""
    if request.method == "POST":
        try:
            action = request.form.get("action")

            if action == "restart_monitoring":
                monitor = getattr(current_app.extensions, "activity_monitor", None)
                if monitor:
                    monitor.stop_monitoring()
                    monitor.start_monitoring()
                    return jsonify(
                        {"success": True, "message": _("Monitoring restarted")}
                    )
                return jsonify(
                    {"success": False, "message": _("Monitor not available")}
                )

            if action == "cleanup_old_data":
                activity_service = ActivityService()
                retention_days = int(request.form.get("retention_days", 90))
                deleted_count = activity_service.cleanup_old_activity(retention_days)
                return jsonify(
                    {
                        "success": True,
                        "message": _("Cleaned up {} old activity records").format(
                            deleted_count
                        ),
                    }
                )

            if action == "end_stale_sessions":
                activity_service = ActivityService()
                timeout_hours = int(request.form.get("timeout_hours", 24))
                ended_count = activity_service.end_stale_sessions(timeout_hours)
                return jsonify(
                    {
                        "success": True,
                        "message": _("Ended {} stale sessions").format(ended_count),
                    }
                )

            return jsonify({"success": False, "message": _("Unknown action")})

        except Exception as e:
            logger = structlog.get_logger(__name__)
            logger.error("Failed to update activity settings: %s", e, exc_info=True)
            return jsonify(
                {"success": False, "message": _("Failed to update settings")}
            ), 500

    return _render_activity_settings()


@activity_bp.route("/settings/delete-activity-data", methods=["POST"])
@login_required
def delete_activity_data():
    """Delete all stored activity monitoring data."""
    logger = structlog.get_logger(__name__)

    try:
        deleted = _delete_all_activity_data()
        success_message = _(
            "Activity data has been successfully deleted ({} records)."
        ).format(deleted)
        return _settings_action_response(success=success_message)
    except Exception as exc:
        logger.error("Failed to delete activity data: %s", exc, exc_info=True)
        error_message = _("Failed to delete activity data: {}").format(str(exc))
        return _settings_action_response(error=error_message)


@activity_bp.route("/settings/import-historical-data", methods=["POST"])
@login_required
def import_historical_activity():
    """Import historical viewing data for a selected server."""
    logger = structlog.get_logger(__name__)
    server_id = request.form.get("server_id", type=int)
    days_back = _parse_int("days_back", 30)
    days_back = max(1, min(days_back, 365))
    max_results_raw = request.form.get("max_results")
    max_results = None
    if max_results_raw not in (None, ""):
        parsed_limit = _parse_int("max_results", 0)
        max_results = parsed_limit if parsed_limit > 0 else None

    if not server_id:
        return _settings_action_response(
            error=_("Please select a media server."),
            selected_days_back=days_back,
        )

    try:
        if MediaServer is None:
            raise RuntimeError("Media server model unavailable")

        media_server = MediaServer.query.get(server_id)
        if not media_server:
            return _settings_action_response(
                error=_("Media server not found."),
                selected_server_id=server_id,
                selected_days_back=days_back,
            )

        supported_servers = {"plex", "jellyfin", "emby", "audiobookshelf"}
        server_type = (media_server.server_type or "").lower()

        if server_type not in supported_servers:
            return _settings_action_response(
                error=_(
                    "Historical data import is currently only supported for Plex, Jellyfin, Emby, and AudiobookShelf servers."
                ),
                selected_server_id=server_id,
                selected_days_back=days_back,
            )

        service = HistoricalDataService(server_id)
        job = service.start_async_import(days_back=days_back, max_results=max_results)

        server_label = server_type.title()
        success_message = _(
            "Historical import job #{job_id} started for {server} (last {days} days)."
        ).format(job_id=job.id, server=server_label, days=days_back)
        return _settings_action_response(
            success=success_message,
            selected_server_id=server_id,
            selected_days_back=days_back,
        )

    except Exception as exc:
        logger.error("Failed to import historical data: %s", exc, exc_info=True)
        error_message = _("Failed to import historical data: {}").format(str(exc))
        return _settings_action_response(
            error=error_message,
            selected_server_id=server_id,
            selected_days_back=days_back,
        )


@activity_bp.route("/settings/clear-historical-data", methods=["POST"])
@login_required
def clear_historical_activity():
    """Remove imported historical data for the selected server."""
    logger = structlog.get_logger(__name__)
    server_id = request.form.get("server_id", type=int)

    if not server_id:
        return _settings_action_response(error=_("Please select a media server."))

    try:
        service = HistoricalDataService(server_id)
        result = service.clear_historical_data()

        if result.get("success"):
            success_message = _("Successfully cleared {} historical entries.").format(
                result.get("deleted_count", 0)
            )
            return _settings_action_response(
                success=success_message, selected_server_id=server_id
            )

        error_message = _("Failed to clear historical data: {}").format(
            result.get("error", _("Unknown error"))
        )
        return _settings_action_response(
            error=error_message, selected_server_id=server_id
        )

    except Exception as exc:
        logger.error("Failed to clear historical data: %s", exc, exc_info=True)
        error_message = _("Failed to clear historical data: {}").format(str(exc))
        return _settings_action_response(
            error=error_message, selected_server_id=server_id
        )


@activity_bp.route("/settings/historical-jobs", methods=["GET"])
@login_required
def historical_import_jobs():
    """Return recent historical import jobs for display."""
    server_id = request.args.get("server_id", type=int)
    return _render_historical_jobs_partial(server_id)


@activity_bp.route("/settings/historical-jobs/<int:job_id>/delete", methods=["POST"])
@login_required
def delete_historical_job(job_id: int):
    """Delete a historical import job (typically failed/completed ones)."""
    if HistoricalImportJob is None:
        return "", 204

    server_id = request.form.get("server_id", type=int)
    job = HistoricalImportJob.query.get(job_id)

    if not job:
        return _render_historical_jobs_partial(server_id)

    if job.is_active:
        return (
            jsonify(
                {"error": _("Cannot remove a job that is still queued or running.")}
            ),
            400,
        )

    db.session.delete(job)
    db.session.commit()
    return _render_historical_jobs_partial(server_id)


@activity_bp.route("/settings/historical-data-stats/<int:server_id>")
@login_required
def historical_data_stats(server_id: int):
    """Expose stored historical data statistics for a server."""
    try:
        service = HistoricalDataService(server_id)
        stats = service.get_import_statistics()
        return jsonify(stats)
    except Exception as exc:
        structlog.get_logger(__name__).error(
            "Failed to load historical data stats: %s", exc, exc_info=True
        )
        return (
            jsonify(
                {
                    "total_entries": 0,
                    "unique_users": 0,
                    "date_range": {"oldest": None, "newest": None},
                    "error": _("An internal error has occurred."),
                }
            ),
            500,
        )
