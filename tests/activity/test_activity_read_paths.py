"""
Read paths of the activity pages.

- The history grid groups on reference_id and uses the
  (reference_id, started_at) index.
- Read paths do not resolve identities and do not write to the database.
- The export streams the rows in chunks.
- /activity/summary gives a refresh signal that progress writes do not change.
- The dashboard runs a fixed, small number of aggregate queries.
"""

import csv
import io
import json
from datetime import UTC, datetime, timedelta

import pytest

from app.activity.domain.models import ActivityEvent, ActivityQuery
from app.extensions import db
from app.models import ActivitySession, Identity, User
from app.services.activity.analytics import ActivityAnalyticsService
from app.services.activity.ingestion import ActivityIngestionService
from app.services.activity.queries import ActivityQueryService
from tests.activity.conftest import add_session, count_sql, writes


def test_grid_groups_on_reference_id_without_writes(app, server):
    with app.app_context():
        now = datetime.now(UTC)
        first = add_session(server.id, "a1", now - timedelta(hours=3))
        add_session(
            server.id,
            "a2",
            now - timedelta(hours=2),
            reference_id=first.id,
            media_title="Movie (resumed)",
        )
        add_session(server.id, "b1", now - timedelta(hours=1), user_name="bob")
        # A Wizarr user that matches, but the session row has no link. The
        # read path must not resolve or store it.
        db.session.add(
            User(
                token="t",
                username="alice",
                email="a@x.com",
                code="c",
                server_id=server.id,
            )
        )
        db.session.commit()

        service = ActivityQueryService()
        with count_sql() as record:
            sessions, total = service.get_activity_sessions(
                ActivityQuery(limit=20, offset=0)
            )
            # A later commit in the same request must not write the merged row.
            db.session.commit()

        assert total == 2
        assert [s.session_id for s in sessions] == ["b1", "a1"]
        merged = sessions[1]
        assert merged.media_title == "Movie (resumed)"
        assert merged.get_metadata()["group_count"] == 2
        assert writes(record) == []
        assert not any("FROM user " in s and "lower" in s for s in record["statements"])

        stored = db.session.get(ActivitySession, first.id)
        assert stored.media_title == "Movie"
        assert stored.wizarr_user_id is None


def test_grid_shows_stored_identity(app, server):
    with app.app_context():
        identity = Identity(nickname="Ally")
        db.session.add(identity)
        db.session.flush()
        user = User(
            token="t",
            username="alice",
            email="a@x.com",
            code="c",
            server_id=server.id,
            identity_id=identity.id,
        )
        db.session.add(user)
        db.session.flush()
        add_session(
            server.id,
            "a1",
            datetime.now(UTC),
            wizarr_user_id=user.id,
        )
        db.session.commit()

        sessions, _ = ActivityQueryService().get_activity_sessions(
            ActivityQuery(limit=20)
        )
        assert sessions[0].display_user_name == "Ally"


def test_grid_queries_use_reference_index(app, server):
    with app.app_context():
        service = ActivityQueryService()
        query = ActivityQuery(limit=20, offset=0)
        group_query = service._group_query(query, service._build_filters(query)).limit(
            20
        )
        compiled = group_query.statement.compile(
            dialect=db.engine.dialect, compile_kwargs={"literal_binds": True}
        )
        plan = db.session.connection().exec_driver_sql(f"EXPLAIN QUERY PLAN {compiled}")
        details = " ".join(str(row[-1]) for row in plan)
        assert "ix_activity_session_reference_started" in details
        assert "TEMP B-TREE FOR GROUP BY" not in details


def test_export_iterator_matches_grid(app, server):
    with app.app_context():
        now = datetime.now(UTC)
        rows = []
        for i in range(7):
            rows.append(add_session(server.id, f"s{i}", now - timedelta(minutes=i)))
        # Put two rows in one group.
        add_session(
            server.id, "s7", now - timedelta(minutes=30), reference_id=rows[3].id
        )
        db.session.commit()

        service = ActivityQueryService()
        query = ActivityQuery(start_date=now - timedelta(days=1))
        expected, total = service.get_activity_sessions(query)
        expected_ids = [s.session_id for s in expected]

        streamed = [
            s.session_id for s in service.iter_activity_sessions(query, chunk_size=3)
        ]
        assert streamed == expected_ids
        assert total == 7


def test_export_streams_csv_and_json(app, server, admin_client):
    with app.app_context():
        now = datetime.now(UTC)
        for i in range(3):
            add_session(server.id, f"s{i}", now - timedelta(minutes=i))
        db.session.commit()

    response = admin_client.get("/activity/export?format=csv&days=1")
    assert response.status_code == 200
    assert response.is_streamed
    rows = list(csv.reader(io.StringIO(response.get_data(as_text=True))))
    assert rows[0][0] == "Session ID"
    assert [row[0] for row in rows[1:]] == ["s0", "s1", "s2"]

    response = admin_client.get("/activity/export?format=json&days=1")
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert [item["session_id"] for item in data] == ["s0", "s1", "s2"]


def test_summary_signal_ignores_progress_writes(app, server, admin_client):
    service = ActivityIngestionService()
    with app.app_context():
        started = service.record_activity_event(
            ActivityEvent(
                event_type="session_start",
                server_id=server.id,
                session_id="live",
                user_name="alice",
                media_title="Movie",
                position_ms=0,
                state="playing",
            )
        )
        session_row_id = started.id

    first = admin_client.get("/activity/summary").get_json()
    assert first["active_sessions"] == 1
    assert first["latest_session_id"] == session_row_id

    with app.app_context():
        # A progress write after the throttle interval changes updated_at only.
        db.session.execute(
            db.text(
                "UPDATE activity_session SET updated_at = '2000-01-01 00:00:00' WHERE id = :id"
            ),
            {"id": session_row_id},
        )
        db.session.commit()
        service.record_activity_event(
            ActivityEvent(
                event_type="session_progress",
                server_id=server.id,
                session_id="live",
                user_name="alice",
                media_title="Movie",
                position_ms=90_000,
                state="playing",
            )
        )

    second = admin_client.get("/activity/summary").get_json()
    assert second["latest_updated_at"] != first["latest_updated_at"]
    for key in ("active_sessions", "latest_session_id", "latest_started_at"):
        assert second[key] == first[key]

    with app.app_context():
        service.record_activity_event(
            ActivityEvent(
                event_type="session_end",
                server_id=server.id,
                session_id="live",
                user_name="alice",
                media_title="Movie",
                position_ms=95_000,
                state="stopped",
            )
        )

    third = admin_client.get("/activity/summary").get_json()
    assert third["active_sessions"] == 0


def test_dashboard_stats_values_and_query_count(app, server):
    with app.app_context():
        base = (datetime.now(UTC) - timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        add_session(
            server.id,
            "a",
            base,
            user_name="u1",
            media_title="Film",
            duration_ms=3_600_000,
        )
        add_session(
            server.id,
            "b",
            base + timedelta(hours=11),
            user_name="u2",
            media_type="episode",
            series_name="Show",
            media_title="Show - S01E01",
            duration_ms=1_800_000,
        )
        add_session(
            server.id,
            "c",
            base + timedelta(minutes=5),
            user_name="u1",
            media_type=None,
            media_title="Clip",
            active=True,
            duration_ms=None,
        )
        # Excluded: an Unknown user, and a session outside the window.
        add_session(server.id, "d", base, user_name="Unknown")
        add_session(server.id, "e", base - timedelta(days=30), user_name="u2")
        db.session.commit()

        with count_sql() as record:
            stats = ActivityAnalyticsService().get_dashboard_stats(days=7)

        assert len(record["statements"]) == 6
        assert stats["total_sessions"] == 3
        assert stats["unique_users"] == 2
        assert stats["total_watch_time"] == pytest.approx(1.5)
        assert stats["avg_session_length"] == pytest.approx(0.75)
        assert stats["media_type_labels"] == ["episode", "movie"]
        assert stats["media_type_data"] == [1, 1]

        expected_hours = [0] * 24
        expected_hours[10] = 2
        expected_hours[21] = 1
        assert stats["hourly_data"] == expected_hours
        assert stats["hourly_labels"][0] == "12 AM"
        assert stats["hourly_labels"][13] == "1 PM"

        expected_days = [0] * 7
        expected_days[int(base.strftime("%w"))] = 3
        assert stats["weekday_data"] == expected_days

        assert [u["username"] for u in stats["top_users"]] == ["u1", "u2"]
        assert stats["server_stats"][0]["session_count"] == 3
        assert sum(stats["time_series_data"]) == 3


def test_import_jobs_poll_only_while_a_job_is_active(app, server, admin_client):
    from app.models import HistoricalImportJob

    with app.app_context():
        job = HistoricalImportJob(server_id=server.id, days_back=30, status="running")
        db.session.add(job)
        db.session.commit()
        job_id = job.id

    body = admin_client.get("/activity/settings/historical-jobs").get_data(as_text=True)
    assert "every 8s [document.visibilityState === 'visible']" in body

    with app.app_context():
        db.session.get(HistoricalImportJob, job_id).status = "failed"
        db.session.commit()

    body = admin_client.get("/activity/settings/historical-jobs").get_data(as_text=True)
    assert "every 8s" not in body
