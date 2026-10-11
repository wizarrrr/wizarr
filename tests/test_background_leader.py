"""Tests for the background leader election (app/background.py)."""

import subprocess
import sys
import threading
import time

import click
import pytest
from flask import Flask

import app.background as background

pytestmark = pytest.mark.skipif(
    background.fcntl is None, reason="The leader lock needs fcntl"
)

HOLD_LOCK_SCRIPT = """
import fcntl, os, sys, time
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o600)
fcntl.flock(fd, fcntl.LOCK_EX)
print("locked", flush=True)
time.sleep(60)
"""


@pytest.fixture
def lock_file(tmp_path, monkeypatch):
    """A private lock file, and a clean lock state before and after the test."""
    path = tmp_path / "wizarr-background.lock"
    monkeypatch.setattr(background, "lock_path", lambda: path)
    _release_lock()
    yield path
    _release_lock()


def _release_lock():
    with background._state_lock:
        if background._lock_fd is not None:
            import os

            os.close(background._lock_fd)
        background._lock_fd = None
        background._lock_pid = None


@pytest.fixture
def other_process(lock_file):
    """Another process that holds the leader lock."""
    proc = subprocess.Popen(  # noqa: S603 - fixed test script
        [sys.executable, "-c", HOLD_LOCK_SCRIPT, str(lock_file)],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    assert proc.stdout.readline().strip() == "locked"
    yield proc
    proc.kill()
    proc.wait()


@pytest.fixture
def server_env(monkeypatch):
    """Make the process look like a server process, not a test run."""
    # pytest sets PYTEST_CURRENT_TEST again before each test phase.
    monkeypatch.setattr(background, "_running_under_pytest", lambda: False)
    for name in (
        "FLASK_SKIP_SCHEDULER",
        "WERKZEUG_RUN_MAIN",
        "FLASK_DEBUG",
        background.GUNICORN_MASTER_PID_ENV,
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("_", "/usr/bin/gunicorn")
    monkeypatch.setattr(sys, "argv", ["gunicorn", "run:app"])


@pytest.fixture
def server_app(server_env):
    return Flask("leader-test")


def test_first_process_gets_the_lock(lock_file):
    assert background.acquire_leader_lock(lock_file) is True
    # A second call in the same process keeps the lock.
    assert background.acquire_leader_lock(lock_file) is True
    assert lock_file.read_text().strip().isdigit()


def test_second_process_does_not_get_the_lock(lock_file, other_process):
    assert background.acquire_leader_lock(lock_file) is False


def test_lock_is_free_after_the_leader_exits(lock_file, other_process):
    assert background.acquire_leader_lock(lock_file) is False

    other_process.kill()
    other_process.wait()

    assert background.acquire_leader_lock(lock_file) is True


def test_leader_starts_background_services(server_app, lock_file, monkeypatch):
    started = []
    monkeypatch.setattr(background, "_become_leader", started.append)

    assert background.start_background_services(server_app) == "leader"
    assert started == [server_app]


def test_standby_process_takes_over_when_the_leader_exits(
    server_app, lock_file, other_process, monkeypatch
):
    took_over = threading.Event()

    def become_leader(app):
        app.extensions[background.LEADER_EXTENSION] = True
        took_over.set()

    monkeypatch.setattr(background, "_become_leader", become_leader)

    assert background.start_background_services(server_app) == "standby"
    assert background.is_background_leader(server_app) is False

    other_process.kill()
    other_process.wait()

    assert took_over.wait(timeout=10)
    assert background.is_background_leader(server_app) is True


def test_become_leader_starts_scheduler_activity_and_tasks(server_app, monkeypatch):
    calls = []
    monkeypatch.setattr(background, "_shutdown_hook_registered", True)
    monkeypatch.setattr(background, "_leader_app", None)
    monkeypatch.setattr(
        background, "_run_startup_migrations", lambda app: calls.append("migrations")
    )
    monkeypatch.setattr(
        "app.extensions.init_scheduler", lambda app: calls.append("scheduler") or False
    )
    monkeypatch.setattr("app.activity.init_app", lambda app: calls.append("activity"))
    tasks_done = threading.Event()
    monkeypatch.setattr(background, "_run_startup_tasks", lambda app: tasks_done.set())

    background._become_leader(server_app)

    assert calls == ["migrations", "scheduler", "activity"]
    assert tasks_done.wait(timeout=5)
    assert background.is_background_leader(server_app) is True


def test_tests_never_run_background_services():
    app = Flask("testing-app")
    app.config["TESTING"] = True

    assert background.background_skip_reason(app) == "tests"


@pytest.mark.parametrize(
    ("env", "reason"),
    [
        ({"FLASK_SKIP_SCHEDULER": "true"}, "FLASK_SKIP_SCHEDULER is set"),
        ({"WERKZEUG_RUN_MAIN": "false"}, "Werkzeug reloader parent process"),
    ],
)
def test_skip_reasons_from_environment(server_app, monkeypatch, env, reason):
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    assert background.background_skip_reason(server_app) == reason


def test_gunicorn_master_never_runs_background_services(server_app, monkeypatch):
    import os

    monkeypatch.setenv(background.GUNICORN_MASTER_PID_ENV, str(os.getpid()))
    assert background.background_skip_reason(server_app) == "gunicorn master process"

    monkeypatch.setenv(background.GUNICORN_MASTER_PID_ENV, str(os.getpid() + 1))
    assert background.background_skip_reason(server_app) is None


def test_gunicorn_worker_runs_background_services(server_app):
    assert background.background_skip_reason(server_app) is None


def test_reloader_child_runs_background_services(server_app, monkeypatch):
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")

    assert background.background_skip_reason(server_app) is None


def _reason_in_cli_command(app, name, params):
    command = click.Command(name)
    with click.Context(command, info_name=name) as ctx:
        ctx.params.update(params)
        return background.background_skip_reason(app)


def test_flask_run_with_reloader_parent_is_skipped(server_app, monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "1")

    reason = _reason_in_cli_command(server_app, "run", {"reload": None})

    assert reason == "Werkzeug reloader parent process"


def test_flask_run_without_reloader_is_the_leader(server_app, monkeypatch):
    monkeypatch.setenv("FLASK_DEBUG", "1")

    assert _reason_in_cli_command(server_app, "run", {"reload": False}) is None


def test_other_flask_commands_are_skipped(server_app):
    assert _reason_in_cli_command(server_app, "shell", {}) == "'flask shell' command"


def test_shutdown_stops_a_running_scheduler(monkeypatch):
    class FakeScheduler:
        running = True
        calls = 0

        def shutdown(self, wait):
            self.calls += 1
            self.running = False

    fake = FakeScheduler()
    monkeypatch.setattr("app.extensions.scheduler", fake)
    leader_app = Flask("shutdown-test")
    monkeypatch.setattr(background, "_leader_app", leader_app)
    stopped = []
    monkeypatch.setattr("app.activity.tracking.stop_activity_tracking", stopped.append)

    background.shutdown_background_services()
    background.shutdown_background_services()

    assert fake.calls == 1
    # Stopping the activity monitor is safe more than once.
    assert stopped == [leader_app, leader_app]


def test_create_app_in_tests_is_not_the_leader(app):
    assert background.is_background_leader(app) is False
    # Wait a short time: no standby thread may take the lock in tests.
    time.sleep(0.05)
    assert not any(
        thread.name == "wizarr-background-standby" for thread in threading.enumerate()
    )
