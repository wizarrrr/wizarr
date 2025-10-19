from flask import current_app, request, session
from flask_apscheduler import APScheduler
from flask_babel import Babel
from flask_htmx import HTMX
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_restx import Api
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

# Initialize Flask-RESTX API with OpenAPI configuration
# This will be initialized later with the blueprint in api_routes.py
api = Api(
    title="Wizarr API",
    version="2.2.1",
    description="Multi-server invitation manager for Plex, Jellyfin, Emby & AudiobookShelf",
    doc="/docs/",  # Swagger UI will be available at /api/docs/
    validate=True,
    ordered=True,
)

# Define API key security scheme for OpenAPI
api.authorizations = {
    "apikey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key required for all endpoints",
    }
}


# Initialize with app
def init_extensions(app):
    """Initialize Flask extensions with clean separation of concerns."""
    import os

    # Core extensions initialization
    sess.init_app(app)
    babel.init_app(app, locale_selector=_select_locale)

    # Scheduler initialization - Flask-APScheduler handles Gunicorn properly
    should_skip_scheduler = (
        "pytest" in os.getenv("_", "")
        or os.getenv("PYTEST_CURRENT_TEST")
        or "alembic" in os.getenv("_", "")
        or any("alembic" in str(arg).lower() for arg in __import__("sys").argv)
        or any(
            "db" in str(arg) and ("upgrade" in str(arg) or "migrate" in str(arg))
            for arg in __import__("sys").argv
        )
        or os.getenv("FLASK_SKIP_SCHEDULER") == "true"
        or os.getenv("WIZARR_DISABLE_SCHEDULER", "false").lower()
        in ("true", "1", "yes")
    )

    if not should_skip_scheduler:
        # Configure Flask-APScheduler for Gunicorn compatibility
        app.config["SCHEDULER_API_ENABLED"] = False  # Disable API for security
        app.config["SCHEDULER_JOBSTORE_URL"] = app.config.get("SQLALCHEMY_DATABASE_URI")

        scheduler.init_app(app)

        # Register tasks with the scheduler
        from app.tasks.maintenance import (
            _get_expiry_check_interval,
            check_expiring,
        )
        from app.tasks.update_check import fetch_and_cache_manifest

        # Add the expiry check task to the scheduler, passing the app instance
        scheduler.add_job(
            id="check_expiring",
            func=lambda: check_expiring(app),
            trigger="interval",
            minutes=_get_expiry_check_interval(),
            replace_existing=True,
        )

        # Add the manifest fetch task to run every 24 hours
        scheduler.add_job(
            id="fetch_manifest",
            func=lambda: fetch_and_cache_manifest(app),
            trigger="interval",
            hours=24,
            replace_existing=True,
        )

        # Note: WAL auto-checkpoints every 1000 pages (~4MB) automatically
        # Manual daily checkpoint is optional - only needed if WAL grows large
        # Uncomment if you notice large .db-wal files:
        # scheduler.add_job(
        #     id="checkpoint_wal",
        #     func=lambda: checkpoint_wal_database(app),
        #     trigger="interval",
        #     hours=24,
        #     replace_existing=True,
        # )

        # Start the scheduler - Flask-APScheduler handles Gunicorn coordination
        try:
            if not scheduler.running:
                scheduler.start()
                app.logger.info("APScheduler started successfully")
            else:
                app.logger.info("APScheduler already running")
        except Exception as e:
            app.logger.warning(f"Failed to start APScheduler: {e}")

    # Continue with remaining extensions

    # Continue with remaining extensions
    htmx.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # type: ignore[assignment]
    db.init_app(app)

    # Enable SQLite WAL mode for concurrent writes
    _configure_sqlite_for_concurrency(app)

    migrate.init_app(app, db)
    limiter.init_app(app)
    # Flask-RESTX API will be initialized with the blueprint

    # Always fetch manifest on startup after DB is initialized
    if not should_skip_scheduler:
        try:
            from app.tasks.update_check import fetch_and_cache_manifest

            fetch_and_cache_manifest(app)
        except Exception as e:
            app.logger.info("Initial manifest fetch failed: %s", e)


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
        return db.session.get(AdminAccount, int(user_id))

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


def _configure_sqlite_for_concurrency(app):
    """Configure SQLite for optimal concurrent write performance.

    Enables WAL (Write-Ahead Logging) mode which allows:
    - Multiple readers can access the database simultaneously
    - Writers don't block readers
    - One writer can proceed while readers are active
    - Much better performance for concurrent workloads (4 workers + background threads)

    SAFETY: WAL mode requires local filesystem access. It will automatically
    fall back to DELETE journal mode if the filesystem doesn't support it.
    """
    from sqlalchemy import event

    @event.listens_for(db.engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ARG001
        """Set SQLite pragmas on each new connection."""
        # Only apply to SQLite databases
        if "sqlite" in str(db.engine.url):
            cursor = dbapi_conn.cursor()

            # Try to enable WAL mode - SQLite will refuse if filesystem doesn't support it
            result = cursor.execute("PRAGMA journal_mode=WAL").fetchone()
            journal_mode = result[0] if result else "unknown"

            if journal_mode.lower() != "wal":
                # WAL mode couldn't be enabled (likely network filesystem)
                app.logger.warning(
                    "⚠️  SQLite WAL mode not available (journal_mode=%s). "
                    "This may indicate a network filesystem (NFS/SMB) which can cause corruption. "
                    "For best results, use a local volume mount. "
                    "Falling back to safer DELETE mode with reduced concurrency.",
                    journal_mode,
                )
                # Ensure we're in DELETE mode for safety
                cursor.execute("PRAGMA journal_mode=DELETE")
            else:
                app.logger.info("✅ SQLite WAL mode enabled for concurrent writes")

            # Set busy timeout to 30 seconds (works with all journal modes)
            cursor.execute("PRAGMA busy_timeout=30000")
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            # Synchronous=NORMAL is safe with WAL, but use FULL for non-WAL
            if journal_mode.lower() == "wal":
                cursor.execute("PRAGMA synchronous=NORMAL")
            else:
                cursor.execute("PRAGMA synchronous=FULL")
            # Larger cache size for better performance (10MB)
            cursor.execute("PRAGMA cache_size=-10000")
            # Auto-checkpoint only applies to WAL mode
            if journal_mode.lower() == "wal":
                cursor.execute("PRAGMA wal_autocheckpoint=1000")
            cursor.close()
