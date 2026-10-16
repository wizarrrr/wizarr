"""Run the background work of Wizarr in exactly one process.

Wizarr can run in more than one process at the same time: gunicorn workers,
the Werkzeug reloader, and Flask CLI commands. Only one of these processes
must run the scheduler, the activity monitor and the startup tasks. This
process is the "background leader".

The leader holds an exclusive ``flock`` on a lock file in the database
directory. The operating system releases the lock when the process stops.
A process that does not get the lock waits for it in a daemon thread, so it
becomes the leader when the old leader stops (for example after a gunicorn
reload). If ``fcntl`` is not available (Windows), the process is the leader.
"""

from __future__ import annotations

import atexit
import contextlib
import errno
import logging
import os
import sys
import threading
from pathlib import Path

from flask import Flask, current_app

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

LEADER_EXTENSION = "wizarr_background_leader"
LOCK_FILENAME = "wizarr-background.lock"
STARTUP_DATA_LOCK_FILENAME = "wizarr-startup-data.lock"
GUNICORN_MASTER_PID_ENV = "WIZARR_GUNICORN_MASTER_PID"

logger = logging.getLogger(__name__)

# The open lock file of the leader. Keep it open for the life of the process.
_lock_fd: int | None = None
_lock_pid: int | None = None
_state_lock = threading.Lock()
# The app of the leader, for the shutdown hook.
_leader_app: Flask | None = None
_shutdown_hook_registered = False


def is_background_leader(app: Flask | None = None) -> bool:
    """Return True when this process runs the background work."""
    target = app if app is not None else current_app
    return bool(target.extensions.get(LEADER_EXTENSION, False))


def lock_path() -> Path:
    """Return the path of the leader lock file."""
    from app.config import DATABASE_DIR

    return Path(DATABASE_DIR) / LOCK_FILENAME


@contextlib.contextmanager
def startup_data_lock():
    """Let one process at a time do the startup data work of create_app.

    The wizard-step seed and the wizard migrations insert rows. When two
    gunicorn workers start at the same time, both can insert the same rows,
    and one of them fails with a UNIQUE error. With this lock, the second
    worker waits, then finds the rows and does nothing. The work takes less
    than a second, so the wait is short.
    """
    fd = None
    if fcntl is not None:
        try:
            fd = os.open(
                lock_path().with_name(STARTUP_DATA_LOCK_FILENAME),
                os.O_RDWR | os.O_CREAT,
                0o600,
            )
            fcntl.flock(fd, fcntl.LOCK_EX)
        except OSError as exc:
            logger.warning("Cannot lock the startup data work (%s).", exc)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)


def background_skip_reason(app: Flask) -> str | None:
    """Return why this process must not run background work, or None."""
    if app.config.get("TESTING") or _running_under_pytest():
        return "tests"
    if os.getenv("FLASK_SKIP_SCHEDULER") == "true":
        return "FLASK_SKIP_SCHEDULER is set"
    if _is_migration_command():
        return "database migration command"
    if os.getenv(GUNICORN_MASTER_PID_ENV) == str(os.getpid()):
        return "gunicorn master process"
    if _is_reloader_parent():
        return "Werkzeug reloader parent process"
    command = _flask_cli_command()
    if command is not None and command != "run":
        return f"'flask {command}' command"
    return None


def start_background_services(app: Flask) -> str:
    """Elect the background leader and start the background work in it.

    Returns "leader", "standby" or "skipped".
    """
    app.extensions[LEADER_EXTENSION] = False

    reason = background_skip_reason(app)
    if reason is not None:
        logger.debug("Background services skipped: %s", reason)
        return "skipped"

    path = lock_path()
    if acquire_leader_lock(path):
        _become_leader(app)
        return "leader"

    logger.info(
        "Process %s waits: another process runs the background services",
        os.getpid(),
    )
    _wait_for_leadership(app, path)
    return "standby"


def acquire_leader_lock(path: Path, *, blocking: bool = False) -> bool:
    """Take the exclusive leader lock. Return True when this process has it."""
    global _lock_fd, _lock_pid

    pid = os.getpid()
    with _state_lock:
        if _lock_fd is not None and _lock_pid == pid:
            return True

    if fcntl is None:
        return True

    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as exc:
        logger.warning(
            "Cannot open the background lock file %s (%s). "
            "This process runs the background services.",
            path,
            exc,
        )
        return True

    flags = fcntl.LOCK_EX if blocking else fcntl.LOCK_EX | fcntl.LOCK_NB
    try:
        fcntl.flock(fd, flags)
    except OSError as exc:
        os.close(fd)
        if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES):
            return False
        logger.warning(
            "Cannot lock %s (%s). This process runs the background services.",
            path,
            exc,
        )
        return True

    # Write the PID into the file to help when you debug.
    try:
        os.ftruncate(fd, 0)
        os.write(fd, f"{pid}\n".encode())
    except OSError:
        pass

    with _state_lock:
        _lock_fd = fd
        _lock_pid = pid
    return True


def on_worker_fork(wsgi_app) -> None:
    """Prepare a preloaded app in a new gunicorn worker.

    gunicorn calls this from ``post_fork`` only when the master loaded the
    app before the fork (``--preload``).
    """
    if not isinstance(wsgi_app, Flask):
        return

    from app.extensions import db

    with wsgi_app.app_context():
        # The pool can contain SQLite connections that the master opened.
        # Do not use them in the child, and do not close them for the master.
        for engine in db.engines.values():
            engine.dispose(close=False)

    start_background_services(wsgi_app)


def shutdown_background_services(wait: bool = False) -> None:
    """Stop the scheduler and the activity monitor of this process.

    You can call this function more than once. gunicorn calls it from
    ``worker_exit``. For other servers, the hook from
    ``_register_shutdown_hook()`` calls it.
    """
    from app.extensions import scheduler

    try:
        if scheduler.running:
            scheduler.shutdown(wait=wait)
            logger.info("APScheduler shut down (pid %s)", os.getpid())
    except Exception as exc:
        logger.warning("Error while the APScheduler shuts down: %s", exc)

    # Stop the monitor loop and the collectors, so that no poll or database
    # write is in progress when the process exits.
    leader_app = _leader_app
    if leader_app is not None:
        try:
            from app.activity.tracking import stop_activity_tracking

            stop_activity_tracking(leader_app)
        except Exception as exc:
            logger.warning("Error while the activity monitor stops: %s", exc)


def _register_shutdown_hook() -> None:
    """Call shutdown_background_services() when the interpreter stops.

    ``threading._register_atexit`` callbacks run before the interpreter joins
    the thread pools. ``atexit`` callbacks run after that join, which is too
    late for the scheduler and the activity monitor.
    """
    global _shutdown_hook_registered

    if _shutdown_hook_registered:
        return
    _shutdown_hook_registered = True

    register = getattr(threading, "_register_atexit", None)
    if register is not None:
        try:
            register(shutdown_background_services)
            return
        except RuntimeError:
            pass
    atexit.register(shutdown_background_services)


def _become_leader(app: Flask) -> None:
    """Start the scheduler, the activity monitor and the startup tasks."""
    global _leader_app

    app.extensions[LEADER_EXTENSION] = True
    _leader_app = app
    logger.info("Process %s is the background leader", os.getpid())

    _run_startup_migrations(app)

    _register_shutdown_hook()

    from app.extensions import init_scheduler

    init_scheduler(app)

    try:
        from app.activity import init_app as init_activity

        init_activity(app)
    except Exception as exc:
        logger.warning("Activity monitoring did not start: %s", exc)

    threading.Thread(
        target=_run_startup_tasks,
        args=(app,),
        name="wizarr-startup-tasks",
        daemon=True,
    ).start()


def _wait_for_leadership(app: Flask, path: Path) -> None:
    """Wait for the lock in a daemon thread. Then become the leader."""

    def wait() -> None:
        try:
            if not acquire_leader_lock(path, blocking=True):
                return
            logger.info("Process %s takes over the background services", os.getpid())
            _become_leader(app)
        except Exception:
            logger.exception("Background leader takeover failed")

    threading.Thread(target=wait, name="wizarr-background-standby", daemon=True).start()


def _run_startup_migrations(app: Flask) -> None:
    """Run the old data migrations. They are idempotent.

    gunicorn ran them in the master before. Now the leader runs them, so they
    also run with ``flask run`` and other servers.
    """
    from app.scripts.migrate_libraries import (
        run_library_migration,
        update_server_verified,
    )
    from app.scripts.migrate_media_server import migrate_single_to_multi

    for migration in (
        update_server_verified,
        run_library_migration,
        migrate_single_to_multi,
    ):
        # Each migration uses its own app context. The context teardown
        # removes the session, so a failed migration does not leave an open
        # transaction.
        try:
            migration(app)
        except Exception as exc:
            logger.warning("Startup migration %s failed: %s", migration.__name__, exc)


def _run_startup_tasks(app: Flask) -> None:
    """Run the slow startup work after the app accepts requests."""
    from app.tasks.maintenance import optimize_sqlite_database

    optimize_sqlite_database(app)

    try:
        with app.app_context():
            from app.services.library_scanner import scan_all_server_libraries

            total_scanned, errors = scan_all_server_libraries(show_logs=False)
        logger.info("Startup library scan: %s libraries scanned", total_scanned)
        for error in errors:
            logger.warning("Startup library scan: %s", error)
    except Exception as exc:
        logger.warning("Startup library scan failed: %s", exc)


def _running_under_pytest() -> bool:
    return "pytest" in os.getenv("_", "") or bool(os.getenv("PYTEST_CURRENT_TEST"))


def _is_migration_command() -> bool:
    argv = [str(arg).lower() for arg in sys.argv]
    if "alembic" in os.getenv("_", "") or any("alembic" in arg for arg in argv):
        return True
    return any("db" in arg and ("upgrade" in arg or "migrate" in arg) for arg in argv)


def _click_context():
    try:
        import click
    except ImportError:  # pragma: no cover - click is a Flask dependency
        return None
    return click.get_current_context(silent=True)


def _flask_cli_command() -> str | None:
    """Return the name of the running Flask CLI command, or None."""
    ctx = _click_context()
    return ctx.info_name if ctx is not None else None


def _is_reloader_parent() -> bool:
    """Return True in the parent process of the Werkzeug reloader.

    Flask 3 loads the app in the parent and in the child process. Only the
    child serves requests, so only the child can be the leader.
    """
    run_main = os.environ.get("WERKZEUG_RUN_MAIN")
    if run_main == "true":
        return False
    if run_main == "false":
        return True

    ctx = _click_context()
    if ctx is None or ctx.info_name != "run":
        return False

    reload = ctx.params.get("reload")
    if reload is None:
        from flask.helpers import get_debug_flag

        reload = get_debug_flag()
    return bool(reload)
