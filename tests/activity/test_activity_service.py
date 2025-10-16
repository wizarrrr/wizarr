from app.activity.domain.models import ActivityQuery
from app.services.activity import ActivityService


def test_activity_service_dashboard_stats_without_db():
    service = ActivityService()
    stats = service.get_dashboard_stats()

    assert isinstance(stats, dict)
    assert stats["total_sessions"] == 0
    assert "time_series_labels" in stats


def test_activity_service_query_without_db():
    service = ActivityService()
    sessions, total = service.get_activity_sessions(ActivityQuery())

    assert sessions == []
    assert total == 0
