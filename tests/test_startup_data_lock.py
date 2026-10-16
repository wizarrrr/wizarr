import threading
import time

import pytest

from app import background

pytest.importorskip("fcntl")


def test_startup_data_lock_makes_processes_wait(tmp_path, monkeypatch):
    monkeypatch.setattr(background, "lock_path", lambda: tmp_path / "leader.lock")
    order: list[str] = []
    first_has_lock = threading.Event()

    def first():
        with background.startup_data_lock():
            order.append("first-start")
            first_has_lock.set()
            time.sleep(0.2)
            order.append("first-end")

    def second():
        first_has_lock.wait()
        # flock conflicts between two open file descriptions, also in one
        # process, so this thread acts like a second worker.
        with background.startup_data_lock():
            order.append("second")

    threads = [threading.Thread(target=first), threading.Thread(target=second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert order == ["first-start", "first-end", "second"]
    assert (tmp_path / background.STARTUP_DATA_LOCK_FILENAME).exists()


def test_startup_data_lock_continues_when_the_file_cannot_open(tmp_path, monkeypatch):
    monkeypatch.setattr(
        background, "lock_path", lambda: tmp_path / "missing-dir" / "leader.lock"
    )
    ran = False
    with background.startup_data_lock():
        ran = True
    assert ran
