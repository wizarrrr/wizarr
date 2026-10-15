import os
import threading
from unittest.mock import Mock

import pytest

from app.models import ExpiredUser
from app.services import expiry
from tests.expiry_helpers import add_expired_users

fcntl = pytest.importorskip("fcntl")


@pytest.fixture
def lock_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.DATABASE_DIR", tmp_path)
    return tmp_path


def test_second_process_run_does_nothing_while_lock_is_held(
    app, session, monkeypatch, lock_dir
):
    with app.app_context():
        add_expired_users(session, action="disable")
        disable_user = Mock(return_value=True)
        monkeypatch.setattr(expiry, "disable_user", disable_user)
        monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)

        # Another process holds the lock: a separate open file description
        # conflicts with flock in the same way.
        fd = os.open(lock_dir / expiry.EXPIRY_LOCK_FILENAME, os.O_RDWR | os.O_CREAT)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            assert expiry.disable_or_delete_user_if_expired() == []
        finally:
            os.close(fd)

        disable_user.assert_not_called()
        assert ExpiredUser.query.count() == 0


def test_run_in_other_thread_does_nothing_while_run_is_active(
    app, session, monkeypatch, lock_dir
):
    with app.app_context():
        user_id = add_expired_users(session, action="disable")[0]
        monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)

        second_result: list[list[int]] = []

        def disable_and_start_second_run(db_id, commit=True):
            # The first run is in its remote call. A second run starts now.
            thread = threading.Thread(
                target=lambda: second_result.append(
                    _run_in_app(app, expiry.disable_or_delete_user_if_expired)
                )
            )
            thread.start()
            thread.join()
            return True

        monkeypatch.setattr(expiry, "disable_user", disable_and_start_second_run)

        assert expiry.disable_or_delete_user_if_expired() == [user_id]
        assert second_result == [[]]
        assert ExpiredUser.query.count() == 1


def test_lock_is_released_after_a_run(app, session, monkeypatch, lock_dir):
    with app.app_context():
        user_id = add_expired_users(session, action="disable")[0]
        monkeypatch.setattr(expiry, "disable_user", Mock(return_value=True))
        monkeypatch.setattr(expiry.time, "sleep", lambda _seconds: None)

        assert expiry.disable_or_delete_user_if_expired() == [user_id]

        with expiry._expiry_run_lock() as acquired:
            assert acquired is True


def _run_in_app(app, func):
    with app.app_context():
        return func()
