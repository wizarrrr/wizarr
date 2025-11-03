"""
Query services for Wizarr activity data.

This module focuses on read-oriented operations (lists, detail views, filters)
so API layers can depend on a smaller surface area than the full ingestion
service.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog

try:
    from app.extensions import db  # type: ignore
except ImportError:  # pragma: no cover - during unit tests
    db = None  # type: ignore

from sqlalchemy import or_

from app.activity.domain.models import ActivityQuery
from app.models import ActivitySession
from app.services.activity.identity_resolution import apply_identity_resolution


class ActivityQueryService:
    """Encapsulates filterable queries over activity sessions."""

    def __init__(self):
        self.logger = structlog.get_logger(__name__)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def get_activity_sessions(
        self,
        query: ActivityQuery,
    ) -> tuple[list[ActivitySession], int]:
        """Return activity sessions matching the supplied query object."""
        if db is None:
            return [], 0

        try:
            from sqlalchemy import case, func

            from app.models import MediaServer  # Local import to avoid cycles

            group_key_expr = case(
                (
                    ActivitySession.reference_id.isnot(None),
                    ActivitySession.reference_id,
                ),
                else_=ActivitySession.id,
            )

            filters = []
            if query.server_ids:
                filters.append(ActivitySession.server_id.in_(query.server_ids))
            if query.user_names:
                # Replace exact match with partial, case-insensitive match for each name
                filters.append(
                    or_(
                        *[
                            ActivitySession.user_name.ilike(f"%{name}%")
                            for name in query.user_names
                        ]
                    )
                )
            if query.media_types:
                filters.append(ActivitySession.media_type.in_(query.media_types))
            if query.start_date:
                filters.append(ActivitySession.started_at >= query.start_date)
            if query.end_date:
                filters.append(ActivitySession.started_at <= query.end_date)
            if query.active_only:
                filters.append(ActivitySession.active.is_(True))

            total_count = (
                db.session.query(func.count(func.distinct(group_key_expr)))
                .filter(*filters)
                .scalar()
                or 0
            )

            if total_count == 0:
                return [], 0

            order_col = getattr(
                ActivitySession, query.order_by, ActivitySession.started_at
            )
            direction = (query.order_direction or "desc").lower()
            order_agg = (
                func.max(order_col) if direction == "desc" else func.min(order_col)
            )
            order_value = order_agg.label("order_value")

            limit_value = query.limit if query.limit not in (None, 0) else None
            offset_value = query.offset or 0

            group_query = (
                db.session.query(group_key_expr.label("group_key"), order_value)
                .filter(*filters)
                .group_by(group_key_expr)
            )

            if direction == "desc":
                group_query = group_query.order_by(
                    order_value.desc(), group_key_expr.desc()
                )
            else:
                group_query = group_query.order_by(
                    order_value.asc(), group_key_expr.asc()
                )

            if offset_value:
                group_query = group_query.offset(offset_value)
            if limit_value:
                group_query = group_query.limit(limit_value)

            group_rows = group_query.all()
            if not group_rows:
                return [], total_count

            group_keys = [row.group_key for row in group_rows]
            group_order_map = {key: index for index, key in enumerate(group_keys)}

            session_query = (
                db.session.query(
                    ActivitySession,
                    MediaServer.name.label("server_name"),
                    MediaServer.server_type.label("server_type"),
                )
                .outerjoin(MediaServer, ActivitySession.server_id == MediaServer.id)
                .filter(*filters)
            )

            if group_keys and (limit_value is not None or offset_value):
                session_query = session_query.filter(group_key_expr.in_(group_keys))

            if direction == "desc":
                session_query = session_query.order_by(
                    order_col.desc(),
                    ActivitySession.id.desc(),
                )
            else:
                session_query = session_query.order_by(
                    order_col.asc(),
                    ActivitySession.id.asc(),
                )

            results = session_query.all()

            raw_sessions: list[ActivitySession] = []
            for session_obj, server_name, server_type in results:
                session_obj.server_name = server_name
                session_obj.server_type = server_type
                raw_sessions.append(session_obj)

            identity_updates = False
            for session in raw_sessions:
                try:
                    identity_updates |= bool(apply_identity_resolution(session))
                except Exception as exc:  # pragma: no cover - defensive
                    self.logger.debug("Identity resolution skipped: %s", exc)

            if identity_updates:
                try:
                    db.session.commit()
                except Exception as exc:  # pragma: no cover - best effort
                    self.logger.debug("Failed to persist identity resolution: %s", exc)
                    db.session.rollback()

            sessions = self._consolidate_grouped_sessions(raw_sessions)

            if group_order_map:
                sessions.sort(
                    key=lambda s: group_order_map.get(
                        s.reference_id if s.reference_id is not None else s.id,
                        len(group_order_map),
                    )
                )

            if limit_value is not None and len(sessions) > len(group_keys):
                sessions = sessions[: len(group_keys)]

            if query.include_snapshots:
                for session in sessions:
                    _ = session.snapshots

            return sessions, total_count

        except Exception as exc:  # pragma: no cover - log and fallback
            self.logger.error("Failed to get activity sessions: %s", exc, exc_info=True)
            return [], 0

    def get_active_sessions(
        self, server_id: int | None = None
    ) -> list[ActivitySession]:
        """Return all currently active sessions, optionally filtered by server."""
        query = ActivityQuery(
            server_ids=[server_id] if server_id else None,
            active_only=True,
            order_by="started_at",
            order_direction="desc",
        )
        sessions, _ = self.get_activity_sessions(query)
        return sessions

    def get_user_activity(
        self, user_name: str, days: int = 30
    ) -> list[ActivitySession]:
        """Return sessions for a specific user within the requested window."""
        start_date = datetime.now(UTC) - timedelta(days=days)
        query = ActivityQuery(
            user_names=[user_name],
            start_date=start_date,
            order_by="started_at",
            order_direction="desc",
        )
        sessions, _ = self.get_activity_sessions(query)
        return sessions

    def get_server_activity(
        self, server_id: int, days: int = 7
    ) -> list[ActivitySession]:
        """Return sessions for a specific server."""
        start_date = datetime.now(UTC) - timedelta(days=days)
        query = ActivityQuery(
            server_ids=[server_id],
            start_date=start_date,
            order_by="started_at",
            order_direction="desc",
        )
        sessions, _ = self.get_activity_sessions(query)
        return sessions

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _consolidate_grouped_sessions(
        self,
        sessions: list[ActivitySession],
    ) -> list[ActivitySession]:
        """Collapse grouped sessions (reference_id) into a single representative."""
        if not sessions:
            return []

        grouped = {}
        standalone_sessions: list[ActivitySession] = []

        for session in sessions:
            if session.reference_id is not None:
                grouped.setdefault(session.reference_id, []).append(session)
            else:
                standalone_sessions.append(session)

        consolidated_sessions: list[ActivitySession] = []

        for group_sessions in grouped.values():
            if len(group_sessions) == 1:
                consolidated_sessions.append(group_sessions[0])
            else:
                consolidated_sessions.append(self._merge_session_group(group_sessions))

        consolidated_sessions.extend(standalone_sessions)
        consolidated_sessions.sort(
            key=lambda s: s.started_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return consolidated_sessions

    def _merge_session_group(self, sessions: list[ActivitySession]) -> ActivitySession:
        """Merge a set of grouped sessions into a single consolidated view."""
        if not sessions:
            raise ValueError("Cannot merge empty session list")

        if len(sessions) == 1:
            return sessions[0]

        sorted_sessions = sorted(
            sessions,
            key=lambda s: s.started_at or datetime.max.replace(tzinfo=UTC),
        )

        base_session = sorted_sessions[0]
        latest_session = sorted_sessions[-1]
        is_active = any(getattr(s, "active", False) for s in sessions)

        consolidated = base_session
        consolidated.user_name = latest_session.user_name
        consolidated.user_id = latest_session.user_id
        consolidated.media_title = latest_session.media_title
        consolidated.media_type = latest_session.media_type
        consolidated.media_id = latest_session.media_id
        consolidated.series_name = latest_session.series_name
        consolidated.season_number = latest_session.season_number
        consolidated.episode_number = latest_session.episode_number

        consolidated.started_at = base_session.started_at
        consolidated.active = is_active
        consolidated.duration_ms = latest_session.duration_ms

        consolidated.device_name = latest_session.device_name
        consolidated.client_name = latest_session.client_name
        consolidated.ip_address = latest_session.ip_address
        consolidated.platform = latest_session.platform
        consolidated.player_version = latest_session.player_version

        if latest_session.transcoding_info:
            consolidated.set_transcoding_info(latest_session.get_transcoding_info())
        else:
            consolidated.transcoding_info = None

        if latest_session.session_metadata:
            consolidated.set_metadata(latest_session.get_metadata())
        else:
            consolidated.session_metadata = None

        consolidated.artwork_url = latest_session.artwork_url
        consolidated.thumbnail_url = latest_session.thumbnail_url
        consolidated.updated_at = latest_session.updated_at

        if hasattr(base_session, "server_name"):
            consolidated.server_name = base_session.server_name
        if hasattr(base_session, "server_type"):
            consolidated.server_type = base_session.server_type

        metadata = consolidated.get_metadata()
        metadata["grouped_sessions"] = [s.session_id for s in sessions]
        metadata["group_count"] = len(sessions)
        consolidated.set_metadata(metadata)

        return consolidated
