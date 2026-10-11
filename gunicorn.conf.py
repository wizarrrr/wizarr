# Gunicorn configuration with clean logging
#
# The master process does not import the Flask app. Each worker creates the
# app when it starts. One worker becomes the "background leader" (see
# app/background.py). Only that worker runs the scheduler, the activity
# monitor, the startup migrations and the startup tasks.
import logging
import os
import sys

# Make log level configurable for debugging production issues
# Set GUNICORN_LOG_LEVEL=info or debug for verbose output
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "warning").lower()
accesslog = None  # Disable access logs for clean output
errorlog = "-"  # Only errors to stderr

# Wizarr uses SQLite. Keep one process by default, and use threads for
# request concurrency. With more workers, only one worker runs background work.
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
worker_class = "gthread"

# Worker timeout - kill workers that don't respond within this time
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# Make host and port configurable
host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "5690")
bind = f"{host}:{port}"

# Record the PID of the master. When the app is preloaded (--preload), the
# master creates the app. app/background.py uses this value to keep the
# background work out of the master.
os.environ["WIZARR_GUNICORN_MASTER_PID"] = str(os.getpid())


def when_ready(server):  # noqa: ARG001
    """Called in the master after the server is started."""
    print(
        f"INFO: Gunicorn master {os.getpid()} ready on {bind} "
        f"(workers={workers}, threads={threads})",
        flush=True,
    )


def post_fork(server, worker):  # noqa: ARG001
    """Called in the worker after the fork, before the worker loads the app."""
    if not server.cfg.preload_app:
        return

    # With --preload, the master created the app before the fork. Drop the
    # inherited database connections and elect the leader in this worker.
    from app.background import on_worker_fork

    on_worker_fork(server.app.wsgi())


def post_worker_init(worker):
    """Worker process initialization - runs once per worker after the app loads."""
    try:
        # Set worker environment
        os.environ["GUNICORN_WORKER_PID"] = str(worker.pid)

        # The worker creates the app and runs the background jobs, so keep the
        # "app" loggers at the level from app/logging_config.py.
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
    except Exception as e:
        print(f"ERROR: Worker {worker.pid} failed to initialize: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        raise


def worker_exit(server, worker):  # noqa: ARG001
    """Called in the worker process when it exits (crash or graceful shutdown)."""
    print(f"WARNING: Worker {worker.pid} exited (age: {worker.age}s)", flush=True)

    # Stop the scheduler and the activity monitor here, before the
    # interpreter shuts down its thread pools. This prevents "cannot schedule
    # new futures" errors and a worker that does not exit. If this process
    # never loaded the app, there is nothing to stop.
    background = sys.modules.get("app.background")
    if background is not None:
        background.shutdown_background_services()


def worker_abort(worker):
    """Called when a worker receives SIGABRT (usually due to timeout)."""
    print(
        f"ERROR: Worker {worker.pid} aborted (timeout or critical error)",
        file=sys.stderr,
    )
    import traceback

    traceback.print_stack()


def on_exit(server):  # noqa: ARG001
    """Called just before the master process exits."""
    print("INFO: Gunicorn master process shutting down", flush=True)
