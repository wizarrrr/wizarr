from flask import current_app, request, session
from flask_apscheduler import APScheduler
from flask_babel import Babel
from flask_htmx import HTMX
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy

# Instantiate extensions
db = SQLAlchemy()
babel = Babel()
sess = Session()
scheduler = APScheduler()
htmx = HTMX()
login_manager = LoginManager()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # No default limits
    storage_uri="memory://",
    enabled=False,  # Explicitly disabled by default
)


# Initialize with app
def init_extensions(app):
    import os

    sess.init_app(app)
    babel.init_app(app, locale_selector=_select_locale)

    # Always initialize scheduler (scheduler runs by default to fix issue #756)
    # Only skip if explicitly disabled via environment variable, in test environment, or during migrations
    is_testing = "pytest" in os.getenv("_", "") or os.getenv("PYTEST_CURRENT_TEST")
    is_migration = (
        "alembic" in os.getenv("_", "")
        or any("alembic" in str(arg).lower() for arg in __import__("sys").argv)
        or any(
            "db" in str(arg) and ("upgrade" in str(arg) or "migrate" in str(arg))
            for arg in __import__("sys").argv
        )
        or os.getenv("FLASK_SKIP_SCHEDULER") == "true"
    )

    if (
        not is_testing
        and not is_migration
        and os.getenv("WIZARR_DISABLE_SCHEDULER", "false").lower()
        not in (
            "true",
            "1",
            "yes",
        )
    ):
        print("🕒 Initializing scheduler for background tasks...")
        scheduler.init_app(app)

        # Import tasks to register them with the scheduler
        from app.tasks import maintenance  # noqa: F401

        # Only start scheduler if not in gunicorn worker context (gunicorn.conf.py will handle starting in master)
        # Check for both gunicorn context and if we're in a worker process
        is_gunicorn = os.getenv("SERVER_SOFTWARE", "").startswith("gunicorn")
        is_worker = os.getenv("GUNICORN_WORKER_PID") is not None

        if not is_gunicorn and not is_worker:
            scheduler.start()
            # Determine frequency message based on WIZARR_ENABLE_SCHEDULER (dev mode indicator)
            if os.getenv("WIZARR_ENABLE_SCHEDULER", "false").lower() in (
                "true",
                "1",
                "yes",
            ):
                print(
                    "✅ Scheduler started - expiry cleanup will run every 1 minute (development mode)"
                )
            else:
                print(
                    "✅ Scheduler started - expiry cleanup will run every 15 minutes (production mode)"
                )
    else:
        if is_testing:
            print("⚠️ Scheduler disabled during testing")
        elif is_migration:
            print("⚠️ Scheduler disabled during database migration")
        else:
            print(
                "⚠️ Scheduler disabled via WIZARR_DISABLE_SCHEDULER environment variable"
            )

    htmx.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # type: ignore[assignment]
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    """Translate *user_id* from the session back into a user instance.

    Two cases are supported for backward-compatibility:

    1. ``"admin"`` – legacy constant representing the sole admin account
       backed by ``Settings`` rows.  We keep it around so existing sessions
       remain valid after upgrading.
    2. A decimal string – primary key of an ``AdminAccount`` row.
    """

    from .models import (  # imported lazily to avoid circular deps
        AdminAccount,
        AdminUser,
    )

    # ── legacy single-admin token ───────────────────────────────────────────
    if user_id == "admin":
        return AdminUser()

    # ── new multi-admin accounts ───────────────────────────────────────────
    if user_id.isdigit():
        return AdminAccount.query.get(int(user_id))

    return None


def _select_locale():
    if forced := current_app.config.get("FORCE_LANGUAGE"):
        return forced
    if arg := request.args.get("lang"):
        session["lang"] = arg
        return arg
    return session.get(
        "lang",
        request.accept_languages.best_match(current_app.config["LANGUAGES"].keys()),
    )
