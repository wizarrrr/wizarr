"""
Analytics services for Wizarr activity data.

Contains aggregate/statistical queries used by dashboards and reports.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

try:
    from app.extensions import db  # type: ignore
except ImportError:  # pragma: no cover - during unit tests
    db = None  # type: ignore

from app.models import ActivitySession


class ActivityAnalyticsService:
    """Provides statistical views over activity sessions."""

    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    @staticmethod
    def _valid_for_statistics_filter():
        """
        Return SQLAlchemy filter to exclude sessions with Unknown values.

        Follows Tautulli's approach: capture all sessions immediately,
        but filter out incomplete ones from statistics and dashboards.

        Note: device_name can be NULL for historical imports, so we allow
        NULL values but exclude "Unknown" string values.
        """
        unknown_values = [
            "Unknown",
            "unknown",
            "Unknown User",
            "unknown user",
            "Unknown Device",
            "unknown device",
        ]
        return db.and_(
            ActivitySession.user_name.not_in(unknown_values),
            ActivitySession.media_title.not_in(unknown_values),
            db.or_(
                ActivitySession.device_name.is_(None),
                ActivitySession.device_name.not_in(unknown_values),
            ),
        )

    def get_activity_stats(self, days: int = 30) -> dict[str, Any]:
        """Return high-level statistics for the given window (excludes Unknown sessions)."""
        if db is None:
            return {}

        try:
            start_date = datetime.now(UTC) - timedelta(days=days)
            valid_filter = self._valid_for_statistics_filter()

            # Filter out sessions with Unknown values for accurate statistics
            total_sessions = (
                db.session.query(ActivitySession)
                .filter(ActivitySession.started_at >= start_date, valid_filter)
                .count()
            )

            unique_users = (
                db.session.query(ActivitySession.user_name)
                .filter(ActivitySession.started_at >= start_date, valid_filter)
                .distinct()
                .count()
            )

            active_sessions = (
                db.session.query(ActivitySession)
                .filter(ActivitySession.active.is_(True), valid_filter)
                .count()
            )

            media_type_stats = (
                db.session.query(
                    ActivitySession.media_type,
                    db.func.count(ActivitySession.id).label("count"),
                )
                .filter(
                    ActivitySession.started_at >= start_date,
                    ActivitySession.media_type.is_not(None),
                    valid_filter,
                )
                .group_by(ActivitySession.media_type)
                .order_by(db.func.count(ActivitySession.id).desc())
                .limit(10)
                .all()
            )

            user_stats = (
                db.session.query(
                    ActivitySession.user_name,
                    db.func.count(ActivitySession.id).label("session_count"),
                )
                .filter(ActivitySession.started_at >= start_date, valid_filter)
                .group_by(ActivitySession.user_name)
                .order_by(db.func.count(ActivitySession.id).desc())
                .limit(10)
                .all()
            )

            return {
                "period_days": days,
                "total_sessions": total_sessions,
                "unique_users": unique_users,
                "active_sessions": active_sessions,
                "media_type_breakdown": [
                    {"media_type": stat[0], "count": stat[1]}
                    for stat in media_type_stats
                ],
                "top_users": [
                    {"user_name": stat[0], "session_count": stat[1]}
                    for stat in user_stats
                ],
            }

        except Exception as exc:  # pragma: no cover - log and fallback
            self.logger.error("Failed to get activity stats: %s", exc, exc_info=True)
            return {}

    def get_dashboard_stats(self, days: int = 7) -> dict[str, Any]:
        """Return the rich dataset used by the activity dashboard (excludes Unknown sessions)."""
        if db is None:
            return self._get_empty_dashboard_stats()

        try:
            from sqlalchemy import and_, case, extract, func, or_

            from app.models import MediaServer

            filters = []
            start_date = None
            if days != 0:
                start_date = datetime.now(UTC) - timedelta(days=days)
                filters.append(ActivitySession.started_at >= start_date)

            # Always filter out sessions with Unknown values for accurate dashboard stats
            filters.append(self._valid_for_statistics_filter())

            watch_time_expr = case(
                (
                    and_(
                        ActivitySession.duration_ms.is_not(None),
                        ActivitySession.duration_ms > 0,
                    ),
                    ActivitySession.duration_ms,
                ),
                else_=0,
            )

            total_sessions_query = db.session.query(func.count(ActivitySession.id))
            unique_users_query = db.session.query(
                func.count(func.distinct(ActivitySession.user_name))
            )
            total_watch_query = db.session.query(
                func.coalesce(func.sum(watch_time_expr), 0)
            )
            watched_sessions_query = db.session.query(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    ActivitySession.duration_ms.is_not(None),
                                    ActivitySession.duration_ms > 0,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                )
            )

            if filters:
                total_sessions_query = total_sessions_query.filter(*filters)
                unique_users_query = unique_users_query.filter(*filters)
                total_watch_query = total_watch_query.filter(*filters)
                watched_sessions_query = watched_sessions_query.filter(*filters)

            total_sessions = total_sessions_query.scalar() or 0
            unique_users = unique_users_query.scalar() or 0
            total_watch_ms = total_watch_query.scalar() or 0
            watched_sessions = watched_sessions_query.scalar() or 0

            avg_session_ms = (
                total_watch_ms / watched_sessions if watched_sessions else 0
            )
            total_watch_hours = total_watch_ms / (1000 * 60 * 60)

            def apply_filters(query):
                return query.filter(*filters) if filters else query

            media_type_data = (
                apply_filters(
                    db.session.query(
                        ActivitySession.media_type,
                        func.count(ActivitySession.id).label("count"),
                    ).filter(ActivitySession.media_type.is_not(None))
                )
                .group_by(ActivitySession.media_type)
                .all()
            )

            # Collapse episodes/seasons under their series so top content reflects movies vs. series.
            media_type_lower = func.lower(func.coalesce(ActivitySession.media_type, ""))
            series_condition = or_(
                ActivitySession.series_name.is_not(None),
                media_type_lower.in_(("episode", "season", "series")),
            )

            top_title_expr = case(
                (
                    series_condition,
                    func.coalesce(
                        ActivitySession.series_name, ActivitySession.media_title
                    ),
                ),
                else_=ActivitySession.media_title,
            ).label("display_title")

            top_type_expr = case(
                (series_condition, "Series"),
                (media_type_lower == "movie", "Movie"),
                else_=func.coalesce(ActivitySession.media_type, "Unknown"),
            ).label("content_type")

            top_content = (
                apply_filters(
                    db.session.query(
                        top_title_expr,
                        top_type_expr,
                        func.count(ActivitySession.id).label("play_count"),
                        func.sum(watch_time_expr).label("total_time"),
                    ).filter(
                        or_(
                            ActivitySession.media_title.is_not(None),
                            ActivitySession.series_name.is_not(None),
                        )
                    )
                )
                .group_by(top_title_expr, top_type_expr)
                .order_by(func.count(ActivitySession.id).desc())
                .limit(10)
                .all()
            )

            top_users = (
                apply_filters(
                    db.session.query(
                        ActivitySession.user_name,
                        func.count(ActivitySession.id).label("session_count"),
                        func.sum(watch_time_expr).label("total_time"),
                    )
                )
                .group_by(ActivitySession.user_name)
                .order_by(func.sum(watch_time_expr).desc())
                .limit(10)
                .all()
            )

            time_series = (
                apply_filters(
                    db.session.query(
                        func.date(ActivitySession.started_at).label("date"),
                        func.count(ActivitySession.id).label("count"),
                    )
                )
                .group_by(func.date(ActivitySession.started_at))
                .order_by(func.date(ActivitySession.started_at))
                .all()
            )

            hourly_distribution = (
                apply_filters(
                    db.session.query(
                        extract("hour", ActivitySession.started_at).label("hour"),
                        func.count(ActivitySession.id).label("count"),
                    )
                )
                .group_by(extract("hour", ActivitySession.started_at))
                .all()
            )

            weekday_distribution = (
                apply_filters(
                    db.session.query(
                        func.strftime("%w", ActivitySession.started_at).label(
                            "weekday"
                        ),
                        func.count(ActivitySession.id).label("count"),
                    )
                )
                .group_by(func.strftime("%w", ActivitySession.started_at))
                .all()
            )

            join_condition = MediaServer.id == ActivitySession.server_id
            for filter_expr in filters:
                join_condition = and_(join_condition, filter_expr)

            server_stats = (
                db.session.query(
                    MediaServer.id,
                    MediaServer.name,
                    MediaServer.server_type,
                    func.count(ActivitySession.id).label("session_count"),
                    func.count(func.distinct(ActivitySession.user_name)).label(
                        "unique_users"
                    ),
                    func.coalesce(func.sum(watch_time_expr), 0).label("total_time"),
                )
                .outerjoin(ActivitySession, join_condition)
                .group_by(
                    MediaServer.id,
                    MediaServer.name,
                    MediaServer.server_type,
                )
                .all()
            )

            dates: list[str] = []
            counts: list[int] = []
            if start_date:
                current_date = start_date.date()
                end_date = datetime.now(UTC).date()

                date_counts = {}
                for row in time_series:
                    raw_date = getattr(row, "date", None)
                    if raw_date is None:
                        continue

                    if hasattr(raw_date, "isoformat"):
                        normalized_date = (
                            raw_date.date() if hasattr(raw_date, "date") else raw_date
                        )
                    elif isinstance(raw_date, str):
                        try:
                            normalized_date = (
                                datetime.strptime(raw_date, "%Y-%m-%d")
                                .replace(tzinfo=UTC)
                                .date()
                            )
                        except (ValueError, TypeError):
                            continue
                    else:
                        continue

                    date_counts[normalized_date] = int(getattr(row, "count", 0) or 0)

                while current_date <= end_date:
                    dates.append(current_date.strftime("%m/%d"))
                    counts.append(date_counts.get(current_date, 0))
                    current_date += timedelta(days=1)
            else:
                from datetime import datetime as dt

                for row in time_series:
                    try:
                        date_obj = (
                            dt.strptime(row.date, "%Y-%m-%d").replace(tzinfo=UTC).date()
                        )
                        dates.append(date_obj.strftime("%m/%d"))
                        counts.append(row.count)
                    except (ValueError, AttributeError):
                        continue

            media_labels = [row.media_type or "Unknown" for row in media_type_data]
            media_counts = [row.count for row in media_type_data]

            hourly_labels = []
            hourly_data = [0] * 24
            hour_counts = {int(row.hour): row.count for row in hourly_distribution}
            for hour in range(24):
                if hour == 0:
                    hourly_labels.append("12 AM")
                elif hour < 12:
                    hourly_labels.append(f"{hour} AM")
                elif hour == 12:
                    hourly_labels.append("12 PM")
                else:
                    hourly_labels.append(f"{hour - 12} PM")
                hourly_data[hour] = hour_counts.get(hour, 0)

            weekday_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            weekday_labels = weekday_names
            weekday_data = [0] * 7
            day_counts = {int(row.weekday): row.count for row in weekday_distribution}
            for day in range(7):
                weekday_data[day] = day_counts.get(day, 0)

            return {
                "total_sessions": total_sessions,
                "unique_users": unique_users,
                "total_watch_time": total_watch_hours,
                "avg_session_length": avg_session_ms / (1000 * 60 * 60)
                if avg_session_ms
                else 0,
                "top_content": [
                    {
                        "title": row.display_title,
                        "media_type": row.content_type or "Unknown",
                        "play_count": row.play_count,
                        "total_time": row.total_time / (1000 * 60 * 60)
                        if row.total_time
                        else 0,
                    }
                    for row in top_content
                ],
                "top_users": [
                    {
                        "username": row.user_name,
                        "session_count": row.session_count,
                        "total_time": row.total_time / (1000 * 60 * 60)
                        if row.total_time
                        else 0,
                    }
                    for row in top_users
                ],
                "time_series_labels": dates,
                "time_series_data": counts,
                "media_type_labels": media_labels,
                "media_type_data": media_counts,
                "hourly_labels": hourly_labels,
                "hourly_data": hourly_data,
                "weekday_labels": weekday_labels,
                "weekday_data": weekday_data,
                "server_stats": [
                    {
                        "id": row.id,
                        "name": row.name,
                        "type": row.server_type,
                        "session_count": row.session_count or 0,
                        "unique_users": row.unique_users or 0,
                        "total_time": row.total_time / (1000 * 60 * 60)
                        if row.total_time
                        else 0,
                    }
                    for row in server_stats
                ],
            }

        except Exception as exc:  # pragma: no cover - log and fallback
            self.logger.error("Failed to get dashboard stats: %s", exc, exc_info=True)
            return self._get_empty_dashboard_stats()

    def _get_empty_dashboard_stats(self) -> dict[str, Any]:
        """Return an empty dataset used when analytics are unavailable."""
        return {
            "total_sessions": 0,
            "unique_users": 0,
            "total_watch_time": 0,
            "avg_session_length": 0,
            "top_content": [],
            "top_users": [],
            "time_series_labels": [],
            "time_series_data": [],
            "media_type_labels": [],
            "media_type_data": [],
            "hourly_labels": ["12 AM"]
            + [f"{i} AM" for i in range(1, 12)]
            + ["12 PM"]
            + [f"{i} PM" for i in range(1, 12)],
            "hourly_data": [0] * 24,
            "weekday_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            "weekday_data": [0] * 7,
            "server_stats": [],
        }


__all__ = ["ActivityAnalyticsService"]
