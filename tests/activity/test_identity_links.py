"""
Wizarr user links of activity sessions.

The identity cache keeps (server, user name) -> (user id, identity id). These
tests check that a commit that adds, deletes or renames a user clears the
cache, that an integrity error from an old cached id does not lose the event,
and that a session without a user gets a link when the user is added later.
"""

from datetime import UTC, datetime, timedelta
from itertools import count

import pytest
from sqlalchemy import delete

from app.extensions import db
from app.models import ActivitySession, Identity, User
from app.services.activity import identity_resolution, ingestion
from app.services.activity.identity_resolution import resolve_user_identity_cached
from tests.activity.conftest import count_sql, make_event, set_updated_at, user_queries

_numbers = count(1)


def add_user(server_id, username, **values):
    number = next(_numbers)
    user = User(
        token=f"token-{number}",
        username=username,
        email=f"{username}-{number}@example.com",
        code=f"code-{number}",
        server_id=server_id,
        **values,
    )
    db.session.add(user)
    db.session.commit()
    return user


def cached_user_id(server_id, name):
    return resolve_user_identity_cached(server_id, name)[0]


# ----------------------------------------------------------------------
# Cache invalidation
# ----------------------------------------------------------------------
def test_new_user_clears_cached_miss(app, server):
    with app.app_context():
        assert cached_user_id(server.id, "carol") is None

        user = add_user(server.id, "carol")

        assert cached_user_id(server.id, "carol") == user.id


@pytest.mark.parametrize("style", ["orm", "query", "statement"])
def test_deleted_user_clears_cache(app, server, style):
    with app.app_context():
        user = add_user(server.id, "bob")
        user_id = user.id
        assert cached_user_id(server.id, "bob") == user_id

        if style == "orm":
            db.session.delete(user)
        elif style == "query":
            db.session.query(User).filter_by(id=user_id).delete()
        else:
            db.session.execute(delete(User).where(User.id == user_id))
        db.session.commit()

        assert cached_user_id(server.id, "bob") is None


def test_renamed_user_and_identity_clear_cache(app, server):
    with app.app_context():
        user = add_user(server.id, "bob")
        assert cached_user_id(server.id, "bob") == user.id

        user.username = "robert"
        db.session.commit()
        assert cached_user_id(server.id, "bob") is None

        identity = Identity(nickname="Rob")
        db.session.add(identity)
        db.session.flush()
        user.identity_id = identity.id
        db.session.commit()
        assert cached_user_id(server.id, "rob") == user.id

        identity.nickname = "Bobby"
        db.session.commit()
        assert cached_user_id(server.id, "rob") is None


def test_other_user_changes_keep_cache(app, server):
    with app.app_context():
        user = add_user(server.id, "bob")
        user_id = user.id
        cached_user_id(server.id, "bob")

        user.notes = "VIP"
        user.expires = datetime.now(UTC) + timedelta(days=30)
        db.session.commit()

        with count_sql() as record:
            assert cached_user_id(server.id, "bob") == user_id
        assert user_queries(record) == []


def test_lookup_during_a_clear_is_not_stored(app, server, monkeypatch):
    with app.app_context():
        add_user(server.id, "bob")
        real_lookup = identity_resolution._lookup
        calls = []

        def lookup_with_concurrent_commit(server_id, name):
            calls.append(name)
            result = real_lookup(server_id, name)
            # Another thread commits a user change during the lookup.
            identity_resolution.clear_identity_cache()
            return result

        monkeypatch.setattr(
            identity_resolution, "_lookup", lookup_with_concurrent_commit
        )
        cached_user_id(server.id, "bob")
        cached_user_id(server.id, "bob")

        assert calls == ["bob", "bob"]


# ----------------------------------------------------------------------
# Ingestion with old cached ids
# ----------------------------------------------------------------------
@pytest.fixture
def integrity_retries(monkeypatch):
    """Record each cache clear that the ingestion service does on an error."""
    calls = []
    real = ingestion.clear_identity_cache

    def recording():
        calls.append(True)
        real()

    monkeypatch.setattr(ingestion, "clear_identity_cache", recording)
    return calls


def test_reinvited_user_links_new_session(app, server, service, integrity_retries):
    with app.app_context():
        old_user = add_user(server.id, "bob")
        old_id = old_user.id
        add_user(server.id, "zed")
        service.record_activity_event(
            make_event("session_start", server.id, session_id="a", user_name="bob")
        )
        service.record_activity_event(
            make_event("session_end", server.id, session_id="a", user_name="bob")
        )

        # The admin deletes the user and invites "bob" again.
        db.session.query(User).filter_by(id=old_id).delete()
        db.session.commit()
        db.session.expunge_all()
        new_user = add_user(server.id, "bob")
        assert new_user.id != old_id

        started = service.record_activity_event(
            make_event("session_start", server.id, session_id="b", user_name="bob")
        )

        assert started is not None
        row = ActivitySession.query.filter_by(session_id="b").one()
        assert row.wizarr_user_id == new_user.id
        # The commits cleared the cache. No insert failed.
        assert integrity_retries == []


def test_integrity_error_clears_cache_and_retries(
    app, server, service, integrity_retries
):
    with app.app_context():
        user = add_user(server.id, "bob")
        user_id = user.id
        service.record_activity_event(
            make_event("session_start", server.id, session_id="a", user_name="bob")
        )
        service.record_activity_event(
            make_event("session_end", server.id, session_id="a", user_name="bob")
        )

        # Raw SQL does not run the ORM events, as a change in another process.
        db.session.execute(db.text("DELETE FROM user WHERE id = :id"), {"id": user_id})
        db.session.commit()
        db.session.expunge_all()
        assert cached_user_id(server.id, "bob") == user_id

        started = service.record_activity_event(
            make_event("session_start", server.id, session_id="b", user_name="bob")
        )

        assert started is not None
        assert integrity_retries == [True]
        row = ActivitySession.query.filter_by(session_id="b").one()
        assert row.active is True
        assert row.wizarr_user_id is None


# ----------------------------------------------------------------------
# Late links
# ----------------------------------------------------------------------
@pytest.fixture
def resolve_calls(monkeypatch):
    """Count the identity resolutions of the ingestion service."""
    calls = []
    real = ingestion.resolve_user_identity_cached

    def counting(server_id, name):
        calls.append(name)
        return real(server_id, name)

    monkeypatch.setattr(ingestion, "resolve_user_identity_cached", counting)
    return calls


def test_session_links_user_added_after_start(app, server, service, resolve_calls):
    with app.app_context():
        started = service.record_activity_event(
            make_event("session_start", server.id, user_name="carol")
        )
        row_id = started.id
        assert started.wizarr_user_id is None

        identity = Identity(nickname="Caro")
        db.session.add(identity)
        db.session.flush()
        user = add_user(server.id, "carol", identity_id=identity.id)

        # A poll that writes nothing does not resolve the user again.
        service.record_activity_event(
            make_event("session_progress", server.id, user_name="carol", position_ms=5)
        )
        assert resolve_calls == []
        assert db.session.get(ActivitySession, row_id).wizarr_user_id is None

        # The next write links the user.
        service.record_activity_event(
            make_event("session_pause", server.id, user_name="carol", state="paused")
        )
        row = db.session.get(ActivitySession, row_id)
        assert row.wizarr_user_id == user.id
        assert row.wizarr_identity_id == identity.id
        assert row.user_name == "Caro"

        # A linked session does not resolve again on later writes.
        resolve_calls.clear()
        service.record_activity_event(
            make_event("session_resume", server.id, user_name="carol")
        )
        assert resolve_calls == []


def test_paused_session_links_user_on_keepalive_write(app, server, service):
    with app.app_context():
        started = service.record_activity_event(
            make_event("session_start", server.id, user_name="carol", state="paused")
        )
        row_id = started.id
        user = add_user(server.id, "carol")

        set_updated_at(row_id, datetime.now(UTC) - timedelta(minutes=31))
        service.record_activity_event(
            make_event("session_progress", server.id, user_name="carol", state="paused")
        )

        assert db.session.get(ActivitySession, row_id).wizarr_user_id == user.id


def test_session_end_links_user_added_after_start(app, server, service):
    with app.app_context():
        started = service.record_activity_event(
            make_event("session_start", server.id, user_name="carol")
        )
        row_id = started.id
        user = add_user(server.id, "carol")

        service.record_activity_event(
            make_event("session_end", server.id, user_name="carol", state="stopped")
        )

        row = db.session.get(ActivitySession, row_id)
        assert row.active is False
        assert row.wizarr_user_id == user.id


def test_unlinked_session_resolves_once_per_write(app, server, service, resolve_calls):
    with app.app_context():
        service.record_activity_event(
            make_event("session_start", server.id, user_name="owner")
        )
        for state in ("paused", "playing", "paused"):
            service.record_activity_event(
                make_event(
                    "session_progress", server.id, user_name="owner", state=state
                )
            )

        # One resolution for each of the three writes. The cache answers.
        assert resolve_calls == ["owner", "owner", "owner"]
