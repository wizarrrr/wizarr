"""The expiry job does not hold the SQLite write lock during remote calls.

Before, the job inserted the ExpiredUser row first and then called the media
server, LDAP and the companion apps inside the open transaction, and slept one
second for each user in it. Every other writer waited. After one failure,
``ROLLBACK TO`` kept the outer transaction open for the rest of the loop.
"""

import sqlite3
from unittest.mock import Mock

import pytest
import requests

from app.extensions import db
from app.models import ExpiredUser, User
from app.services import expiry
from app.services.media import service
from tests.expiry_helpers import add_expired_users


def _write_lock_is_free() -> bool:
    """Try to take the write lock from another connection, without waiting."""
    path = db.engine.url.database
    conn = sqlite3.connect(path, timeout=0)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ROLLBACK")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()


@pytest.fixture
def lock_checks(monkeypatch):
    """Record if the write lock was free at each remote call and each sleep."""
    checks: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        expiry.time, "sleep", lambda _s: checks.append(("sleep", _write_lock_is_free()))
    )
    return checks


def _remote_client(monkeypatch, checks, *, fail_tokens=()):
    client = Mock()

    def remote(name):
        def call(identifier):
            checks.append((name, _write_lock_is_free()))
            if identifier in fail_tokens:
                raise requests.ConnectionError("server down")
            return True

        return call

    client.delete_user.side_effect = remote("delete")
    client.disable_user.side_effect = remote("disable")
    monkeypatch.setattr(service, "get_client_for_media_server", lambda _s: client)
    return client


def test_remote_delete_runs_without_the_write_lock(session, monkeypatch, lock_checks):
    user_ids = add_expired_users(session, count=2, action="delete")
    _remote_client(monkeypatch, lock_checks)

    assert expiry.disable_or_delete_user_if_expired() == user_ids

    assert [name for name, _ in lock_checks] == ["delete", "sleep"] * 2
    assert all(free for _, free in lock_checks)
    assert User.query.count() == 0
    assert ExpiredUser.query.count() == 2


def test_remote_disable_runs_without_the_write_lock(session, monkeypatch, lock_checks):
    user_ids = add_expired_users(session, count=2, action="disable")
    _remote_client(monkeypatch, lock_checks)

    assert expiry.disable_or_delete_user_if_expired() == user_ids

    assert [name for name, _ in lock_checks] == ["disable", "sleep"] * 2
    assert all(free for _, free in lock_checks)
    assert all(db.session.get(User, uid).is_disabled for uid in user_ids)
    assert ExpiredUser.query.count() == 2


def test_failure_does_not_keep_a_transaction_open(session, monkeypatch, lock_checks):
    """After a failed user, the next remote call still runs without the lock."""
    first_id, second_id = add_expired_users(session, count=2, action="delete")
    _remote_client(monkeypatch, lock_checks, fail_tokens={"remote-0"})

    assert expiry.disable_or_delete_user_if_expired() == [second_id]

    assert [name for name, _ in lock_checks] == ["delete", "delete", "sleep"]
    assert all(free for _, free in lock_checks)
    # The failed user stays for the next run, without an expiry event.
    assert db.session.get(User, first_id) is not None
    assert db.session.get(User, second_id) is None
    assert [e.original_user_id for e in ExpiredUser.query.all()] == [second_id]
    assert _write_lock_is_free()


def test_legacy_delete_runs_without_the_write_lock(session, monkeypatch, lock_checks):
    user_ids = add_expired_users(session, count=2, action="delete")
    _remote_client(monkeypatch, lock_checks)

    assert expiry.delete_user_if_expired() == user_ids

    assert [name for name, _ in lock_checks] == ["delete", "sleep"] * 2
    assert all(free for _, free in lock_checks)
    assert ExpiredUser.query.count() == 2
