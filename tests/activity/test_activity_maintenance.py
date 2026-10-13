"""
Retention cleanup, backfill, job registration and historical import batching.
"""

from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models import (
    ActivitySession,
    ActivitySnapshot,
    Identity,
    User,
)
from app.services.activity.ingestion import KEEPALIVE_INTERVAL
from app.services.activity.maintenance import (
    STARTUP_RECOVERY_CUTOFF,
    ActivityMaintenanceService,
)
from app.services.historical import HistoricalDataService
from app.tasks.activity import register_activity_tasks
from tests.activity.conftest import add_session, count_sql, set_updated_at


def test_cleanup_deletes_in_batches(app, server):
    with app.app_context():
        old = datetime.now(UTC) - timedelta(days=200)
        for i in range(5):
            row = add_session(server.id, f"old{i}", old + timedelta(minutes=i))
            db.session.add(
                ActivitySnapshot(session_id=row.id, position_ms=0, state="playing")
            )
        recent = add_session(server.id, "recent", datetime.now(UTC))
        db.session.commit()
        recent_id = recent.id

        with count_sql() as record:
            deleted = ActivityMaintenanceService().cleanup_old_activity(
                retention_days=90, batch_size=2
            )

        assert deleted == 5
        # Batches of 2, 2 and 1 rows: one commit per batch.
        assert record["commits"] == 3
        assert [row.id for row in ActivitySession.query.all()] == [recent_id]
        assert ActivitySnapshot.query.count() == 0


def test_backfill_sets_reference_and_user_links(app, server):
    with app.app_context():
        identity = Identity(nickname="Ally")
        db.session.add(identity)
        db.session.flush()
        user = User(
            token="t",
            username="Alice",
            email="a@x.com",
            code="c",
            server_id=server.id,
            identity_id=identity.id,
        )
        db.session.add(user)
        updated_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        first = add_session(server.id, "s1", datetime.now(UTC), user_name="alice")
        second = add_session(server.id, "s2", datetime.now(UTC), user_name="alice")
        owner = add_session(server.id, "s3", datetime.now(UTC), user_name="owner")
        db.session.commit()
        ids = [first.id, second.id, owner.id]
        # Rows from before the backfill have no reference_id.
        db.session.execute(
            db.text(
                "UPDATE activity_session"
                " SET reference_id = NULL, updated_at = '2025-01-01 12:00:00'"
            )
        )
        db.session.commit()

        with count_sql() as record:
            ActivityMaintenanceService().backfill_session_links()

        # One identity lookup for each distinct user name, not for each row.
        lookups = [s for s in record["statements"] if "lower(user.username)" in s]
        assert len(lookups) == 2

        db.session.expire_all()
        rows = {row.id: row for row in ActivitySession.query.all()}
        for row_id in ids:
            assert rows[row_id].reference_id == row_id
            assert rows[row_id].updated_at.replace(tzinfo=UTC) == updated_at
        assert rows[first.id].wizarr_user_id == user.id
        assert rows[second.id].wizarr_identity_id == identity.id
        assert rows[owner.id].wizarr_user_id is None


class RecordingScheduler:
    def __init__(self):
        self.jobs = {}

    def add_job(self, **kwargs):
        self.jobs[kwargs["id"]] = kwargs

    def get_job(self, job_id):
        return self.jobs.get(job_id)


def test_cleanup_job_schedules(app):
    scheduler = RecordingScheduler()
    before = datetime.now(UTC)
    register_activity_tasks(app, scheduler)

    cleanup = scheduler.jobs["activity_cleanup"]
    stale = scheduler.jobs["activity_stale_cleanup"]
    assert cleanup["hours"] == 24
    assert stale["hours"] == 6
    # The retention cleanup deletes history. Its first run comes one full
    # interval after the start, as before (no early first run).
    assert "next_run_time" not in cleanup
    # The stale-session job deletes no history. It runs soon after the start.
    assert (
        before + timedelta(minutes=1)
        <= stale["next_run_time"]
        <= before + timedelta(minutes=3)
    )
    for job in scheduler.jobs.values():
        assert job["max_instances"] == 1
        assert job["coalesce"] is True


class _DownClient:
    def now_playing(self):
        raise ConnectionError("server down")


def test_startup_recovery_keeps_sessions_inside_the_keepalive_margin(
    app, server, monkeypatch
):
    """A paused session is written once per KEEPALIVE_INTERVAL only.

    When the media server does not answer at startup, the recovery must keep
    such a session, also after a short restart of Wizarr.
    """
    assert STARTUP_RECOVERY_CUTOFF >= 2 * KEEPALIVE_INTERVAL
    monkeypatch.setattr(
        "app.services.media.service.get_client_for_media_server",
        lambda _server: _DownClient(),
    )
    with app.app_context():
        now = datetime.now(UTC)
        paused = add_session(server.id, "paused", now - timedelta(hours=2), active=True)
        gone = add_session(server.id, "gone", now - timedelta(hours=5), active=True)
        db.session.commit()
        paused_id, gone_id = paused.id, gone.id
        # Last keepalive write 30 min before the stop, then 35 min of restart.
        paused_write = now - (KEEPALIVE_INTERVAL + timedelta(minutes=35))
        gone_write = now - STARTUP_RECOVERY_CUTOFF - timedelta(minutes=1)
        set_updated_at(paused_id, paused_write)
        set_updated_at(gone_id, gone_write)

        ended = ActivityMaintenanceService().recover_sessions_on_startup()

        assert ended == 1
        db.session.expire_all()
        assert db.session.get(ActivitySession, paused_id).active is True
        assert db.session.get(ActivitySession, gone_id).active is False


def make_import_row(server_id, i):
    return ActivitySession(
        server_id=server_id,
        session_id=f"historical_{i}",
        user_name="alice",
        media_title=f"Title {i}",
        started_at=datetime.now(UTC) - timedelta(days=1, minutes=i),
        active=False,
        duration_ms=1000,
    )


def test_historical_import_stores_in_batches(app, server):
    with app.app_context():
        add_session(server.id, "historical_0", datetime.now(UTC))
        db.session.commit()

        service = HistoricalDataService(server.id)
        rows = [make_import_row(server.id, i) for i in range(7)]
        # A duplicate inside the same import.
        rows.append(make_import_row(server.id, 3))

        with count_sql() as record:
            stored = service._store_activity_sessions(rows, batch_size=3)

        assert stored == 6
        # Rows 1-6 in batches of 3: two commits.
        assert record["commits"] == 2
        session_inserts = [
            s
            for s in record["statements"]
            if s.startswith("INSERT INTO activity_session")
        ]
        assert len(session_inserts) <= 6

        db.session.expire_all()
        imported = ActivitySession.query.filter(
            ActivitySession.session_id.like("historical_%")
        ).all()
        assert len(imported) == 7
        for row in imported:
            if row.session_id != "historical_0":
                assert row.reference_id == row.id


def test_historical_import_keeps_good_rows_when_one_fails(app, server):
    with app.app_context():
        service = HistoricalDataService(server.id)
        rows = [make_import_row(server.id, i) for i in range(3)]
        rows[1].media_title = None  # NOT NULL column: this row fails.

        stored = service._store_activity_sessions(rows, batch_size=3)

        assert stored == 2
        db.session.expire_all()
        assert {row.session_id for row in ActivitySession.query.all()} == {
            "historical_0",
            "historical_2",
        }
