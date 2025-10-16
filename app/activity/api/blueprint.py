"""
Activity monitoring blueprint for Wizarr.

Provides routes for activity dashboard, analytics, and API endpoints
for managing and viewing media playback activity data.
"""

from datetime import UTC, datetime, timedelta

import structlog
from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import login_required

try:
    from flask_babel import gettext as _

    from app.extensions import db
    from app.models import MediaServer
except ImportError:
    # For testing without Flask app context
    MediaServer = None  # type: ignore[assignment]
    db = None  # type: ignore[assignment]

    def _(x):  # type: ignore[no-redef]
        return x


from app.activity.domain.models import ActivityQuery
from app.models import ActivitySession
from app.services.activity import ActivityService

# Create blueprint
activity_bp = Blueprint(
    "activity",
    __name__,
    url_prefix="/activity",
    template_folder="../templates",
)


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
    if request.method == "GET":
        try:
            # Get monitoring status
            monitor = getattr(current_app.extensions, "activity_monitor", None)
            status = {
                "monitoring_enabled": monitor is not None,
                "connection_status": monitor.get_connection_status() if monitor else {},
            }

            template = (
                "activity/settings_tab.html"
                if request.headers.get("HX-Request")
                else "activity/settings.html"
            )
            return render_template(template, status=status)

        except Exception as e:
            logger = structlog.get_logger(__name__)
            logger.error("Failed to load activity settings: %s", e, exc_info=True)
            template = (
                "activity/settings_tab.html"
                if request.headers.get("HX-Request")
                else "activity/settings.html"
            )
            return render_template(template, error=_("Failed to load settings"))

    else:  # POST
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
