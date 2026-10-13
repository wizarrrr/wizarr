"""Activity statistics API (wizarrrr/wizarr#1455).

The /api/activity endpoints give the Activity dashboard totals, and the
breakdowns per user and per title, to API key holders, for a period.
"""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from app.extensions import db
from app.models import ActivitySession, ApiKey, MediaServer

RAW_KEY = "activity-api-test-key"
HOUR_MS = 60 * 60 * 1000


@pytest.fixture
def activity_data(app, session, admin_user):
    """Two servers, an API key, and sessions inside and outside 30 days."""
    now = datetime.now(UTC)
    with app.app_context():
        db.session.add(
            ApiKey(
                name="activity",
                key_hash=hashlib.sha256(RAW_KEY.encode()).hexdigest(),
                created_by_id=admin_user.id,
                is_active=True,
            )
        )

        plex = MediaServer(
            name="Plex", server_type="plex", url="http://plex", api_key="k"
        )
        jellyfin = MediaServer(
            name="Jellyfin", server_type="jellyfin", url="http://jf", api_key="k"
        )
        db.session.add_all([plex, jellyfin])
        db.session.flush()

        def add(server, user, title, started, duration_ms, active=False, **extra):
            db.session.add(
                ActivitySession(
                    server_id=server.id,
                    session_id=f"{user}-{title}-{started.timestamp()}",
                    user_name=user,
                    media_title=title,
                    started_at=started,
                    duration_ms=duration_ms,
                    active=active,
                    **extra,
                )
            )

        add(
            plex,
            "alice",
            "Inception",
            now - timedelta(days=2),
            2 * HOUR_MS,
            media_type="movie",
        )
        add(
            plex,
            "alice",
            "Pilot",
            now - timedelta(days=3),
            HOUR_MS,
            media_type="episode",
            series_name="Breaking Bad",
        )
        add(
            jellyfin,
            "bob",
            "Cat's in the Bag",
            now - timedelta(days=1),
            HOUR_MS // 2,
            media_type="episode",
            series_name="Breaking Bad",
        )
        # Still playing: a session, but no watch time yet.
        add(
            jellyfin,
            "bob",
            "Inception",
            now - timedelta(hours=1),
            HOUR_MS // 6,
            active=True,
            media_type="movie",
        )
        # Older than the default 30 days.
        add(
            plex,
            "carol",
            "Old Movie",
            now - timedelta(days=60),
            HOUR_MS,
            media_type="movie",
        )
        # Never counted, as on the dashboard.
        add(
            plex,
            "Unknown User",
            "Inception",
            now - timedelta(days=1),
            HOUR_MS,
            media_type="movie",
        )
        db.session.commit()

        return {"plex": plex.id, "jellyfin": jellyfin.id}


def _get(client, path, **params):
    return client.get(path, query_string=params, headers={"X-API-Key": RAW_KEY})


@pytest.mark.parametrize(
    "path", ["/api/activity/stats", "/api/activity/users", "/api/activity/content"]
)
def test_activity_endpoints_require_api_key(client, activity_data, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"X-API-Key": "wrong"}).status_code == 401


def test_stats_default_to_last_30_days(client, activity_data):
    resp = _get(client, "/api/activity/stats")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["start"] is not None
    assert data["end"] is None
    assert data["total_sessions"] == 4
    assert data["unique_users"] == 2
    # Finished sessions only: 2h + 1h + 30min.
    assert data["total_watch_time_seconds"] == 12600
    assert data["avg_session_length_seconds"] == 4200


def test_stats_all_time(client, activity_data):
    data = _get(client, "/api/activity/stats", days=0).get_json()

    assert data["start"] is None
    assert data["total_sessions"] == 5
    assert data["unique_users"] == 3
    assert data["total_watch_time_seconds"] == 16200
    assert data["avg_session_length_seconds"] == 4050


def test_stats_match_activity_dashboard(app, activity_data):
    # Importing app.services.activity before app.activity is circular.
    from app.services.activity.analytics import ActivityAnalyticsService

    with app.app_context():
        service = ActivityAnalyticsService()
        dashboard = service.get_dashboard_stats(days=30)
        start = datetime.now(UTC) - timedelta(days=30)
        summary = service.get_period_summary(start=start)

    assert summary["total_sessions"] == dashboard["total_sessions"]
    assert summary["unique_users"] == dashboard["unique_users"]
    assert summary["total_watch_time_seconds"] == round(
        dashboard["total_watch_time"] * 3600
    )
    assert summary["avg_session_length_seconds"] == round(
        dashboard["avg_session_length"] * 3600
    )


def test_stats_for_date_time_range(client, activity_data):
    now = datetime.now(UTC)
    data = _get(
        client,
        "/api/activity/stats",
        start=(now - timedelta(days=4)).isoformat(),
        end=(now - timedelta(hours=36)).isoformat(),
    ).get_json()

    assert data["total_sessions"] == 2
    assert data["unique_users"] == 1
    assert data["total_watch_time_seconds"] == 10800


def test_date_only_end_includes_the_whole_day(app, client, activity_data):
    with app.app_context():
        db.session.add(
            ActivitySession(
                server_id=activity_data["plex"],
                session_id="late-evening",
                user_name="dave",
                media_title="Late Movie",
                media_type="movie",
                started_at=datetime(2026, 1, 15, 23, 30, tzinfo=UTC),
                duration_ms=HOUR_MS,
                active=False,
            )
        )
        db.session.commit()

    data = _get(
        client, "/api/activity/stats", start="2026-01-15", end="2026-01-15"
    ).get_json()

    assert data["start"] == "2026-01-15T00:00:00+00:00"
    assert data["end"] == "2026-01-16T00:00:00+00:00"
    assert data["total_sessions"] == 1


def test_stats_filter_by_server_and_user(client, activity_data):
    by_server = _get(
        client, "/api/activity/stats", server_id=activity_data["jellyfin"]
    ).get_json()
    assert by_server["total_sessions"] == 2
    assert by_server["unique_users"] == 1
    assert by_server["total_watch_time_seconds"] == 1800

    by_user = _get(client, "/api/activity/stats", username="alice").get_json()
    assert by_user["total_sessions"] == 2
    assert by_user["total_watch_time_seconds"] == 10800


def test_users_breakdown(client, activity_data):
    data = _get(client, "/api/activity/users").get_json()

    assert data["count"] == 2
    assert data["users"] == [
        {"username": "alice", "session_count": 2, "total_watch_time_seconds": 10800},
        {"username": "bob", "session_count": 2, "total_watch_time_seconds": 1800},
    ]

    limited = _get(client, "/api/activity/users", limit=1).get_json()
    assert [u["username"] for u in limited["users"]] == ["alice"]


def test_content_breakdown_groups_episodes_by_series(client, activity_data):
    data = _get(client, "/api/activity/content").get_json()

    assert data["count"] == 2
    assert data["content"] == [
        {
            "title": "Inception",
            "media_type": "Movie",
            "play_count": 2,
            "total_watch_time_seconds": 7200,
        },
        {
            "title": "Breaking Bad",
            "media_type": "Series",
            "play_count": 2,
            "total_watch_time_seconds": 5400,
        },
    ]


@pytest.mark.parametrize(
    ("path", "params", "message"),
    [
        ("/api/activity/stats", {"days": "-1"}, "'days' must be between"),
        ("/api/activity/stats", {"days": "week"}, "'days' must be an integer"),
        ("/api/activity/stats", {"start": "yesterday"}, "'start' must be an ISO"),
        (
            "/api/activity/stats",
            {"days": "7", "start": "2026-01-01"},
            "not both",
        ),
        (
            "/api/activity/stats",
            {"start": "2026-02-01", "end": "2026-01-01"},
            "'start' must be before 'end'",
        ),
        ("/api/activity/stats", {"server_id": "plex"}, "'server_id' must be"),
        ("/api/activity/users", {"limit": "0"}, "'limit' must be between"),
        ("/api/activity/content", {"limit": "5000"}, "'limit' must be between"),
    ],
)
def test_invalid_parameters_return_400(client, activity_data, path, params, message):
    resp = _get(client, path, **params)

    assert resp.status_code == 400
    assert message in resp.get_json()["error"]
