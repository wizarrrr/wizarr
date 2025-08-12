"""Simple structured logging helpers for application startup.

Replaces the complex startup_logger with industry-standard patterns
using Python's standard logging with beautiful formatting.
"""

import logging
import os
import time


class AppLogger:
    """Simple application logger with structured startup messaging."""

    def __init__(self, name: str = "wizarr"):
        self.logger = logging.getLogger(name)
        self._startup_start_time = time.time()
        self._step_count = 0
        self._total_steps = 0

    def welcome(self, version: str = "dev") -> None:
        """Display welcome message with version."""
        print("\n" + "═" * 60)
        print(f"🧙‍♂️ WIZARR v{version}")
        print("   Multi-Server Invitation Manager")
        print("═" * 60)

    def start_sequence(self, total_steps: int = 8) -> None:
        """Initialize startup sequence with total step count."""
        self._total_steps = total_steps
        self._step_count = 0
        self._startup_start_time = time.time()
        print(f"\n🚀 Starting up... ({total_steps} steps)")

    def step(self, message: str, emoji: str = "⚙️") -> None:
        """Log a startup step with progress indicator."""
        self._step_count += 1
        progress = "▓" * self._step_count + "░" * (self._total_steps - self._step_count)
        percentage = (
            round((self._step_count / self._total_steps) * 100)
            if self._total_steps > 0
            else 0
        )

        print(f"   {emoji} {message}")
        print(f"   [{progress}] {percentage}%")

    def success(self, message: str) -> None:
        """Log a successful operation."""
        print(f"   ✅ {message}")

    def warning(self, message: str) -> None:
        """Log a warning message."""
        print(f"   ⚠️  {message}")

    def info(self, message: str) -> None:
        """Log an informational message."""
        print(f"   ℹ️  {message}")

    def error(self, message: str) -> None:
        """Log an error message."""
        print(f"   ❌ {message}")

    def scheduler_status(self, enabled: bool, dev_mode: bool = False) -> None:
        """Log scheduler initialization status."""
        if enabled:
            frequency = "1 minute" if dev_mode else "15 minutes"
            mode = "development" if dev_mode else "production"
            self.success(f"Scheduler active - cleanup every {frequency} ({mode})")
        else:
            self.info("Scheduler disabled")

    def database_migration(self, operation: str, details: str = "") -> None:
        """Log database migration operations."""
        detail_text = f" - {details}" if details else ""
        self.step(f"Database {operation}{detail_text}", "🗄️")

    def complete(self) -> None:
        """Display startup completion message."""
        elapsed = time.time() - self._startup_start_time
        print(f"\n✨ Startup complete in {elapsed:.2f}s")
        print("   Ready to accept connections!")
        print("═" * 60 + "\n")


def is_gunicorn_master() -> bool:
    """Check if running in Gunicorn master process."""
    return os.getenv("SERVER_SOFTWARE", "").startswith("gunicorn") and not os.getenv(
        "GUNICORN_WORKER_PID"
    )


def is_gunicorn_worker() -> bool:
    """Check if running in Gunicorn worker process."""
    return bool(os.getenv("GUNICORN_WORKER_PID"))


def should_show_startup() -> bool:
    """Determine if startup sequence should be shown."""
    import atexit
    import fcntl
    import tempfile

    # Create a lock file to ensure only one process shows startup
    lock_file_path = os.path.join(tempfile.gettempdir(), "wizarr_startup.lock")

    try:
        # Try to acquire exclusive lock
        lock_fd = os.open(lock_file_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        # Clean up lock file on exit
        atexit.register(
            lambda: os.unlink(lock_file_path)
            if os.path.exists(lock_file_path)
            else None
        )

        return True
    except OSError:
        # Another process is already showing startup
        return False
