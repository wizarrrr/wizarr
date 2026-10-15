"""
Write and query budget of activity ingestion.

The collectors send an event for each session on each poll. These tests check
that the ingestion service writes only when something changes, writes a
snapshot only when the playback state changes, writes the position at most
once per minute, resolves identities once per session, and records a poll
cycle in one transaction.
"""

from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models import ActivitySession, ActivitySnapshot, Identity, User
from app.services.activity.identity_resolution import resolve_user_identity
from app.services.activity.ingestion import PLAYBACK_STATE_KEY
from tests.activity.conftest import (
    count_sql,
    make_event,
    set_updated_at,
    user_queries,
    writes,
)


def snapshot_states(session_row_id):
    return [
        row.state
        for row in ActivitySnapshot.query.filter_by(session_id=session_row_id)
        .order_by(ActivitySnapshot.id)
        .all()
    ]


def test_unchanged_progress_does_not_write(app, server, service):
    with app.app_context():
        started = service.record_activity_event(make_event("session_start", server.id))
        session_row_id = started.id

        with count_sql() as record:
            for position in (10_000, 20_000, 30_000, 40_000):
                service.record_activity_event(
                    make_event("session_progress", server.id, position_ms=position)
                )

        assert writes(record) == []
        assert record["commits"] == 0
        assert snapshot_states(session_row_id) == ["playing"]


def test_snapshots_only_on_state_changes(app, server, service):
    with app.app_context():
        started = service.record_activity_event(make_event("session_start", server.id))
        session_row_id = started.id

        service.record_activity_event(
            make_event("session_progress", server.id, position_ms=5_000)
        )
        service.record_activity_event(
            make_event("session_pause", server.id, position_ms=6_000, state="paused")
        )
        service.record_activity_event(
            make_event("session_progress", server.id, position_ms=6_000, state="paused")
        )
        service.record_activity_event(
            make_event("session_resume", server.id, position_ms=6_000, state="playing")
        )
        service.record_activity_event(
            make_event("session_end", server.id, position_ms=9_000, state="stopped")
        )

        assert snapshot_states(session_row_id) == [
            "playing",
            "paused",
            "playing",
            "stopped",
        ]
        row = db.session.get(ActivitySession, session_row_id)
        assert row.active is False
        assert row.get_metadata()["last_known_position_ms"] == 9_000


def test_state_change_writes_at_once(app, server, service):
    with app.app_context():
        started = service.record_activity_event(make_event("session_start", server.id))
        session_row_id = started.id

        with count_sql() as record:
            service.record_activity_event(
                make_event(
                    "session_pause", server.id, position_ms=7_000, state="paused"
                )
            )

        assert record["commits"] == 1
        row = db.session.get(ActivitySession, session_row_id)
        metadata = row.get_metadata()
        assert metadata[PLAYBACK_STATE_KEY] == "paused"
        assert metadata["last_known_position_ms"] == 7_000


def test_position_is_written_after_the_interval(app, server, service):
    with app.app_context():
        started = service.record_activity_event(make_event("session_start", server.id))
        session_row_id = started.id

        # Less than 60 seconds after the last write: no write.
        service.record_activity_event(
            make_event("session_progress", server.id, position_ms=30_000)
        )
        row = db.session.get(ActivitySession, session_row_id)
        assert row.get_metadata().get("last_known_position_ms") != 30_000

        # More than 60 seconds after the last write: the position is written.
        old = datetime.now(UTC) - timedelta(seconds=61)
        set_updated_at(session_row_id, old)
        with count_sql() as record:
            service.record_activity_event(
                make_event("session_progress", server.id, position_ms=61_000)
            )

        assert record["commits"] == 1
        assert not any("activity_snapshot" in s for s in writes(record))
        row = db.session.get(ActivitySession, session_row_id)
        assert row.get_metadata()["last_known_position_ms"] == 61_000
        assert row.updated_at.replace(tzinfo=UTC) > old


def test_paused_session_gets_a_keepalive_write(app, server, service):
    with app.app_context():
        started = service.record_activity_event(
            make_event("session_start", server.id, state="paused")
        )
        session_row_id = started.id

        set_updated_at(session_row_id, datetime.now(UTC) - timedelta(minutes=31))
        with count_sql() as record:
            service.record_activity_event(
                make_event("session_progress", server.id, state="paused")
            )

        assert record["commits"] == 1
        assert snapshot_states(session_row_id) == ["paused"]


def test_meaningful_change_writes_at_once(app, server, service):
    with app.app_context():
        started = service.record_activity_event(make_event("session_start", server.id))
        session_row_id = started.id

        # A new transcoding speed alone is not a meaningful change.
        with count_sql() as record:
            service.record_activity_event(
                make_event(
                    "session_progress",
                    server.id,
                    transcoding_info={
                        "is_transcoding": False,
                        "direct_play": True,
                        "transcoding_speed": 1.4,
                    },
                )
            )
        assert record["commits"] == 0

        # A new stream decision is written at once.
        with count_sql() as record:
            service.record_activity_event(
                make_event(
                    "session_progress",
                    server.id,
                    transcoding_info={"is_transcoding": True, "direct_play": False},
                )
            )
        assert record["commits"] == 1
        row = db.session.get(ActivitySession, session_row_id)
        assert row.get_transcoding_info()["is_transcoding"] is True


def test_poll_cycle_is_one_transaction(app, server, service):
    with app.app_context():
        starts = [
            make_event("session_start", server.id, session_id=f"s{i}", media_id=f"m{i}")
            for i in range(3)
        ]
        with count_sql() as record:
            sessions = service.record_activity_events(starts)
        assert all(s is not None for s in sessions)
        assert record["commits"] == 1

        progress = [
            make_event(
                "session_progress",
                server.id,
                session_id=f"s{i}",
                media_id=f"m{i}",
                position_ms=10_000,
            )
            for i in range(3)
        ]
        with count_sql() as record:
            service.record_activity_events(progress)

        session_selects = [
            s for s in record["statements"] if "FROM activity_session" in s
        ]
        assert record["commits"] == 0
        assert writes(record) == []
        # One query loads the active sessions of the whole cycle, without
        # joins to the user and identity tables.
        assert len(session_selects) == 1
        assert "JOIN" not in session_selects[0].upper()


def test_failed_event_does_not_drop_other_events(app, server, service, monkeypatch):
    with app.app_context():
        original = service._handle_session_start

        def failing_start(event, batch=None):
            if event.session_id == "bad":
                raise RuntimeError("broken event")
            return original(event, batch)

        monkeypatch.setattr(service, "_handle_session_start", failing_start)
        results = service.record_activity_events(
            [
                make_event("session_start", server.id, session_id="good-1"),
                make_event("session_start", server.id, session_id="bad"),
                make_event("session_start", server.id, session_id="good-2"),
            ]
        )

        assert results[1] is None
        stored = {row.session_id for row in ActivitySession.query.all()}
        assert stored == {"good-1", "good-2"}


def test_identity_is_resolved_once_per_session(app, server, service):
    with app.app_context():
        identity = Identity(nickname="Ally", primary_username="alice")
        db.session.add(identity)
        db.session.flush()
        user = User(
            token="t1",
            username="Alice",
            email="alice@example.com",
            code="c1",
            server_id=server.id,
            identity_id=identity.id,
        )
        db.session.add(user)
        db.session.commit()

        with count_sql() as record:
            started = service.record_activity_event(
                make_event("session_start", server.id, user_name="alice")
            )
            for position in (10_000, 20_000, 30_000):
                service.record_activity_event(
                    make_event("session_progress", server.id, position_ms=position)
                )

        assert len(user_queries(record)) == 1
        row = db.session.get(ActivitySession, started.id)
        assert row.user_name == "Ally"
        assert row.wizarr_user_id == user.id
        assert row.wizarr_identity_id == identity.id

        # A second session of the same user uses the cache.
        with count_sql() as record:
            service.record_activity_event(
                make_event("session_start", server.id, session_id="s2", media_id="m2")
            )
        assert user_queries(record) == []


def test_unmatched_user_is_cached(app, server, service):
    with app.app_context():
        with count_sql() as record:
            service.record_activity_event(
                make_event("session_start", server.id, user_name="owner")
            )
        # Three lookups (user name, nickname, primary user name) for a miss.
        assert len(user_queries(record)) == 3

        with count_sql() as record:
            service.record_activity_event(
                make_event(
                    "session_start",
                    server.id,
                    session_id="s2",
                    media_id="m2",
                    user_name="Owner",
                )
            )
        assert user_queries(record) == []


def test_user_name_change_resolves_again(app, server, service):
    with app.app_context():
        user = User(
            token="t2",
            username="bob",
            email="bob@example.com",
            code="c2",
            server_id=server.id,
        )
        db.session.add(user)
        db.session.commit()

        started = service.record_activity_event(
            make_event("session_start", server.id, user_name="Unknown")
        )
        assert started.wizarr_user_id is None

        service.record_activity_event(
            make_event("session_progress", server.id, user_name="bob")
        )
        row = db.session.get(ActivitySession, started.id)
        assert row.user_name == "bob"
        assert row.wizarr_user_id == user.id


def test_identity_lookup_uses_lower_username_index(app, server):
    with app.app_context():
        with count_sql() as record:
            resolve_user_identity(server.id, None, "Somebody")

        index = next(
            i
            for i, statement in enumerate(record["statements"])
            if "lower(user.username)" in statement
        )
        statement = record["statements"][index]
        params = record["params"][index]
        plan = db.session.connection().exec_driver_sql(
            "EXPLAIN QUERY PLAN " + statement, params
        )
        details = " ".join(str(row[-1]) for row in plan)
        assert "ix_user_server_lower_username" in details


def test_new_sessions_always_get_a_reference_id(app, server, service):
    with app.app_context():
        first = service.record_activity_event(make_event("session_start", server.id))
        service.record_activity_event(
            make_event("session_end", server.id, state="stopped")
        )
        second = service.record_activity_event(
            make_event("session_start", server.id, session_id="s2")
        )

        first_row = db.session.get(ActivitySession, first.id)
        second_row = db.session.get(ActivitySession, second.id)
        assert first_row.reference_id == first_row.id
        # Same user and media within two hours: same group.
        assert second_row.reference_id == first_row.id


def test_same_metadata_in_other_python_types_is_not_a_change(app, server, service):
    with app.app_context():
        metadata = {"play_method": "DirectPlay", "streams": ("video", "audio")}
        service.record_activity_event(
            make_event("session_start", server.id, metadata=metadata)
        )

        with count_sql() as record:
            service.record_activity_event(
                make_event("session_progress", server.id, metadata=metadata)
            )

        assert record["commits"] == 0
        assert writes(record) == []


def test_session_end_uses_the_event_time(app, server, service):
    """After a long outage, a collector ends a session at its last good poll."""
    with app.app_context():
        started = service.record_activity_event(make_event("session_start", server.id))
        session_row_id = started.id
        ended_at = datetime.now(UTC) - timedelta(minutes=11)

        service.record_activity_event(
            make_event("session_end", server.id, state="stopped", timestamp=ended_at)
        )

        row = db.session.get(ActivitySession, session_row_id)
        assert row.active is False
        assert row.updated_at.replace(tzinfo=UTC) == ended_at
        assert row.get_metadata()["last_end_timestamp"] == ended_at.isoformat()
