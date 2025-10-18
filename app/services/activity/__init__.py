"""
Service facade for Wizarr activity features.

The facade composes specialised services so callers can continue to use a
single entry point while the implementation remains modular.
"""

from __future__ import annotations

from typing import Any

from app.activity.domain.models import ActivityEvent, ActivityQuery
from app.models import ActivitySession
from app.services.activity.analytics import ActivityAnalyticsService
from app.services.activity.ingestion import ActivityIngestionService
from app.services.activity.maintenance import ActivityMaintenanceService
from app.services.activity.queries import ActivityQueryService


class ActivityService:
    """Backwards-compatible facade that delegates to modular services."""

    def __init__(self):
        self.ingestion = ActivityIngestionService()
        self.queries = ActivityQueryService()
        self.analytics = ActivityAnalyticsService()
        self.maintenance = ActivityMaintenanceService()

    # Event ingestion -------------------------------------------------
    def record_activity_event(self, event: ActivityEvent) -> ActivitySession | None:
        return self.ingestion.record_activity_event(event)

    # Query helpers ---------------------------------------------------
    def get_activity_sessions(
        self,
        query: ActivityQuery,
    ) -> tuple[list[ActivitySession], int]:
        return self.queries.get_activity_sessions(query)

    def get_active_sessions(
        self,
        server_id: int | None = None,
    ) -> list[ActivitySession]:
        return self.queries.get_active_sessions(server_id)

    def get_user_activity(
        self,
        user_name: str,
        days: int = 30,
    ) -> list[ActivitySession]:
        return self.queries.get_user_activity(user_name, days)

    def get_server_activity(
        self,
        server_id: int,
        days: int = 7,
    ) -> list[ActivitySession]:
        return self.queries.get_server_activity(server_id, days)

    # Analytics -------------------------------------------------------
    def get_activity_stats(self, days: int = 30) -> dict[str, Any]:
        return self.analytics.get_activity_stats(days)

    def get_dashboard_stats(self, days: int = 7) -> dict[str, Any]:
        return self.analytics.get_dashboard_stats(days)

    # Maintenance -----------------------------------------------------
    def cleanup_old_activity(self, retention_days: int = 90) -> int:
        return self.maintenance.cleanup_old_activity(retention_days)

    def end_stale_sessions(self, timeout_hours: int = 24) -> int:
        return self.maintenance.end_stale_sessions(timeout_hours)

    def recover_sessions_on_startup(self) -> int:
        return self.maintenance.recover_sessions_on_startup()


__all__ = ["ActivityService"]
