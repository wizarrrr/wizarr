from contextlib import contextmanager

import pytest
from sqlalchemy import event

from app.activity.domain.models import ActivityEvent
from app.extensions import db
from app.models import ActivitySession, MediaServer
from app.services.activity.ingestion import ActivityIngestionService


@pytest.fixture(autouse=True)
def _clear_identity_cache():
    """Start each test with an empty identity cache.

    Test databases reuse row ids, so a cached result from one test can match
    another test.
    """
    from app.services.activity.identity_resolution import clear_identity_cache

    clear_identity_cache()
    yield
    clear_identity_cache()


@pytest.fixture
def server(app, session):
    server = MediaServer(
        name="Activity Server",
        server_type="jellyfin",
        url="http://localhost:8096",
        api_key="key",
        verified=True,
    )
    session.add(server)
    session.commit()
    return server


@pytest.fixture
def service():
    return ActivityIngestionService()


@contextmanager
def count_sql():
    """Collect the statements, parameters and commits that run in the block."""
    record = {"statements": [], "params": [], "commits": 0}

    def before_cursor_execute(conn, cursor, statement, params, context, many):
        record["statements"].append(statement)
        record["params"].append(params)

    def on_commit(conn):
        record["commits"] += 1

    engine = db.engine
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "commit", on_commit)
    try:
        yield record
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(engine, "commit", on_commit)


def writes(record):
    return [
        s
        for s in record["statements"]
        if s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]


def user_queries(record):
    return [s for s in record["statements"] if "FROM user" in s]


def add_session(server_id, session_id, started_at, reference_id=None, **values):
    """Add an ended session row. Without a reference_id, the row is its own group."""
    defaults = {
        "user_name": "alice",
        "media_title": "Movie",
        "media_type": "movie",
        "device_name": "TV",
        "active": False,
        "duration_ms": 600_000,
    }
    defaults.update(values)
    row = ActivitySession(
        server_id=server_id,
        session_id=session_id,
        started_at=started_at,
        **defaults,
    )
    db.session.add(row)
    db.session.flush()
    row.reference_id = reference_id if reference_id is not None else row.id
    return row


def make_event(kind, server_id, session_id="s1", **overrides):
    values = {
        "event_type": kind,
        "server_id": server_id,
        "session_id": session_id,
        "user_name": "alice",
        "media_title": "Movie",
        "media_type": "movie",
        "media_id": "m1",
        "device_name": "TV",
        "position_ms": 0,
        "duration_ms": 7_200_000,
        "state": "playing",
        "transcoding_info": {"is_transcoding": False, "direct_play": True},
        "metadata": {"play_method": "DirectPlay"},
    }
    values.update(overrides)
    return ActivityEvent(**values)


def set_updated_at(session_row_id, value):
    db.session.execute(
        db.text("UPDATE activity_session SET updated_at = :value WHERE id = :id"),
        {"value": value.strftime("%Y-%m-%d %H:%M:%S.%f"), "id": session_row_id},
    )
    db.session.commit()
