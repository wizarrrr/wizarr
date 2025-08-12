"""Centralized startup logger for clean, beautiful initialization messages.

This module provides a single source of truth for all startup logging,
eliminating redundancy and providing a satisfying visual experience.
"""

import os
import time


class StartupLogger:
    """Centralized logger for application startup with process awareness."""

    def __init__(self):
        self._is_master_process = self._detect_master_process()
        self._startup_start_time = time.time()
        self._step_count = 0
        self._total_steps = 0

    def _detect_master_process(self) -> bool:
        """Detect if this is the master process or a worker."""
        # In Gunicorn master process
        is_gunicorn = os.getenv("SERVER_SOFTWARE", "").startswith("gunicorn")
        is_worker = os.getenv("GUNICORN_WORKER_PID") is not None

        # Master process is Gunicorn but not a worker
        # OR Flask development server (not Gunicorn at all)
        return (is_gunicorn and not is_worker) or not is_gunicorn

    def _print_if_master(self, message: str, force: bool = False) -> None:
        """Print message only if this is the master process, unless forced."""
        if self._is_master_process or force:
            print(message, flush=True)

    def welcome(self, version: str = "dev") -> None:
        """Display welcome message with version."""
        if not self._is_master_process:
            return

        print("\n" + "═" * 60)
        print(f"🧙‍♂️ WIZARR v{version}")
        print("   Multi-Server Invitation Manager")
        print("═" * 60)

    def start_sequence(self, total_steps: int = 8) -> None:
        """Initialize startup sequence with total step count."""
        self._total_steps = total_steps
        self._step_count = 0
        self._startup_start_time = time.time()

        if self._is_master_process:
            print(f"\n🚀 Starting up... ({total_steps} steps)")

    def step(self, message: str, emoji: str = "⚙️") -> None:
        """Log a startup step with progress indicator."""
        if not self._is_master_process:
            return

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
        self._print_if_master(f"   ✅ {message}")

    def warning(self, message: str, show_in_workers: bool = False) -> None:
        """Log a warning message."""
        self._print_if_master(f"   ⚠️  {message}", force=show_in_workers)

    def info(self, message: str) -> None:
        """Log an informational message."""
        self._print_if_master(f"   ℹ️  {message}")

    def scheduler_status(self, enabled: bool, dev_mode: bool = False) -> None:
        """Log scheduler initialization status."""
        if not self._is_master_process:
            return

        if enabled:
            frequency = "1 minute" if dev_mode else "15 minutes"
            mode = "development" if dev_mode else "production"
            self.success(f"Scheduler active - cleanup every {frequency} ({mode})")
        else:
            self.info("Scheduler disabled")

    def worker_ready(self, worker_id: str | None = None) -> None:
        """Log worker process ready status (shown only for workers)."""
        if self._is_master_process:
            return

        worker_info = f" [{worker_id}]" if worker_id else ""
        print(f"   👷 Worker ready{worker_info}", flush=True)

    def database_migration(self, operation: str, details: str = "") -> None:
        """Log database migration operations."""
        detail_text = f" - {details}" if details else ""
        self.step(f"Database {operation}{detail_text}", "🗄️")

    def complete(self) -> None:
        """Display startup completion message."""
        if not self._is_master_process:
            return

        elapsed = time.time() - self._startup_start_time
        print(f"\n✨ Startup complete in {elapsed:.2f}s")
        print("   Ready to accept connections!")
        print("═" * 60 + "\n")

    def error(self, message: str, show_in_workers: bool = True) -> None:
        """Log an error message."""
        self._print_if_master(f"   ❌ {message}", force=show_in_workers)


# Global instance for use throughout the application
startup_logger = StartupLogger()
