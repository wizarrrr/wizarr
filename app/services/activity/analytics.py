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

    @staticmethod
    def _watched_condition():
        """Match sessions that count toward watch time.

        A session counts once it has stopped and has a positive duration.
        """
        return db.and_(
            ActivitySession.active.is_(False),
            ActivitySession.duration_ms.is_not(None),
            ActivitySession.duration_ms > 0,
        )

    @classmethod
    def _watch_time_expr(cls):
        """Return the watch time of a session in milliseconds, 0 if it does not count."""
        return db.case(
            (cls._watched_condition(), ActivitySession.duration_ms),
            else_=0,
        )

    @staticmethod
    def _content_group_exprs():
        """Return the (title, type) columns that group sessions by content.

        Episodes and seasons collapse under their series, so the result
        compares movies with series.
        """
        media_type_lower = db.func.lower(
            db.func.coalesce(ActivitySession.media_type, "")
        )
        series_condition = db.or_(
            ActivitySession.series_name.is_not(None),
            media_type_lower.in_(("episode", "season", "series")),
        )

        title_expr = db.case(
            (
                series_condition,
                db.func.coalesce(
                    ActivitySession.series_name, ActivitySession.media_title
                ),
            ),
            else_=ActivitySession.media_title,
        ).label("display_title")

        type_expr = db.case(
            (series_condition, "Series"),
            (media_type_lower == "movie", "Movie"),
            else_=db.func.coalesce(ActivitySession.media_type, "Unknown"),
        ).label("content_type")

        return title_expr, type_expr

    def _period_filters(
        self,
        start: datetime | None,
        end: datetime | None,
        server_id: int | None,
        username: str | None,
    ) -> list:
        """Return the filters for sessions that started in [start, end).

        A missing bound, server or username does not filter. Sessions with
        Unknown values are always excluded.
        """
        filters = [self._valid_for_statistics_filter()]
        if start is not None:
            filters.append(ActivitySession.started_at >= start)
        if end is not None:
            filters.append(ActivitySession.started_at < end)
        if server_id is not None:
            filters.append(ActivitySession.server_id == server_id)
        if username is not None:
            filters.append(ActivitySession.user_name == username)
        return filters

    def get_period_summary(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        server_id: int | None = None,
        username: str | None = None,
    ) -> dict[str, int]:
        """Return the dashboard totals for a period, with durations in seconds."""
        if db is None:
            return {
                "total_sessions": 0,
                "unique_users": 0,
                "total_watch_time_seconds": 0,
                "avg_session_length_seconds": 0,
            }

        filters = self._period_filters(start, end, server_id, username)
        total_sessions, unique_users, watch_ms, watched_sessions = (
            db.session.query(
                db.func.count(ActivitySession.id),
                db.func.count(db.func.distinct(ActivitySession.user_name)),
                db.func.coalesce(db.func.sum(self._watch_time_expr()), 0),
                db.func.coalesce(
                    db.func.sum(db.case((self._watched_condition(), 1), else_=0)),
                    0,
                ),
            )
            .filter(*filters)
            .one()
        )

        return {
            "total_sessions": int(total_sessions or 0),
            "unique_users": int(unique_users or 0),
            "total_watch_time_seconds": round((watch_ms or 0) / 1000),
            "avg_session_length_seconds": round(watch_ms / watched_sessions / 1000)
            if watched_sessions
            else 0,
        }

    def get_user_breakdown(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        server_id: int | None = None,
        username: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return sessions and watch time per user, most watch time first."""
        if db is None:
            return []

        watch_time = db.func.coalesce(db.func.sum(self._watch_time_expr()), 0)
        rows = (
            db.session.query(
                ActivitySession.user_name,
                db.func.count(ActivitySession.id).label("session_count"),
                watch_time.label("total_time"),
            )
            .filter(*self._period_filters(start, end, server_id, username))
            .group_by(ActivitySession.user_name)
            .order_by(
                watch_time.desc(),
                db.func.count(ActivitySession.id).desc(),
                ActivitySession.user_name,
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "username": row.user_name,
                "session_count": row.session_count,
                "total_watch_time_seconds": round(row.total_time / 1000),
            }
            for row in rows
        ]

    def get_content_breakdown(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        server_id: int | None = None,
        username: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return plays and watch time per movie or series, most plays first."""
        if db is None:
            return []

        title_expr, type_expr = self._content_group_exprs()
        watch_time = db.func.coalesce(db.func.sum(self._watch_time_expr()), 0)
        rows = (
            db.session.query(
                title_expr,
                type_expr,
                db.func.count(ActivitySession.id).label("play_count"),
                watch_time.label("total_time"),
            )
            .filter(*self._period_filters(start, end, server_id, username))
            .group_by(title_expr, type_expr)
            .order_by(
                db.func.count(ActivitySession.id).desc(),
                watch_time.desc(),
                title_expr,
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "title": row.display_title,
                "media_type": row.content_type or "Unknown",
                "play_count": row.play_count,
                "total_watch_time_seconds": round(row.total_time / 1000),
            }
            for row in rows
        ]

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

            watch_time_expr = self._watch_time_expr()

            watched_expr = case((self._watched_condition(), 1), else_=0)

            def apply_filters(query):
                return query.filter(*filters) if filters else query

            # One pass for all scalar values (count, distinct users, watch time).
            totals = apply_filters(
                db.session.query(
                    func.count(ActivitySession.id).label("total_sessions"),
                    func.count(func.distinct(ActivitySession.user_name)).label(
                        "unique_users"
                    ),
                    func.coalesce(func.sum(watch_time_expr), 0).label("total_watch_ms"),
                    func.coalesce(func.sum(watched_expr), 0).label("watched_sessions"),
                )
            ).one()

            total_sessions = totals.total_sessions or 0
            unique_users = totals.unique_users or 0
            total_watch_ms = totals.total_watch_ms or 0
            watched_sessions = totals.watched_sessions or 0

            avg_session_ms = (
                total_watch_ms / watched_sessions if watched_sessions else 0
            )
            total_watch_hours = total_watch_ms / (1000 * 60 * 60)

            # One pass for the media type breakdown and the hour and weekday
            # histograms. The result has at most 24 x 7 x (media types) rows.
            hour_expr = extract("hour", ActivitySession.started_at)
            weekday_expr = func.strftime("%w", ActivitySession.started_at)
            distribution_rows = (
                apply_filters(
                    db.session.query(
                        hour_expr.label("hour"),
                        weekday_expr.label("weekday"),
                        ActivitySession.media_type.label("media_type"),
                        func.count(ActivitySession.id).label("count"),
                    )
                )
                .group_by(hour_expr, weekday_expr, ActivitySession.media_type)
                .all()
            )

            media_type_counts: dict[str, int] = {}
            hour_counts: dict[int, int] = {}
            day_counts: dict[int, int] = {}
            for row in distribution_rows:
                count = int(row.count or 0)
                if row.media_type is not None:
                    media_type_counts[row.media_type] = (
                        media_type_counts.get(row.media_type, 0) + count
                    )
                if row.hour is not None:
                    hour = int(row.hour)
                    hour_counts[hour] = hour_counts.get(hour, 0) + count
                if row.weekday is not None:
                    day = int(row.weekday)
                    day_counts[day] = day_counts.get(day, 0) + count

            # SQLite returns GROUP BY results in key order. Keep that order.
            media_type_data = sorted(media_type_counts.items())

            top_title_expr, top_type_expr = self._content_group_exprs()

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

            media_labels = [
                media_type or "Unknown" for media_type, _count in media_type_data
            ]
            media_counts = [count for _media_type, count in media_type_data]

            hourly_labels = []
            hourly_data = [0] * 24
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
