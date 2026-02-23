import os

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
        from app.tasks.ldap_sync import _get_ldap_sync_interval, sync_ldap_users
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

        # Add LDAP user sync task to automatically import new users
        scheduler.add_job(
            id="sync_ldap_users",
            func=lambda: sync_ldap_users(app),
            trigger="interval",
            minutes=_get_ldap_sync_interval(),
            replace_existing=True,
        )

        # Note: WAL auto-checkpoints every 1000 pages (~4MB) automatically.
        # Manual checkpoint jobs can be added here if needed for large .db-wal files.

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


def _normalize_locale(code: str | None) -> str | None:
    """Normalise locale codes to the internal form, handling case and separators."""
    if not code:
        return None

    supported = current_app.config["LANGUAGES"]
    candidate = code.strip()
    if not candidate:
        return None

    candidate = candidate.replace("-", "_")
    lowered_map = {key.lower(): key for key in supported}

    if candidate.lower() in lowered_map:
        return lowered_map[candidate.lower()]

    base = candidate.split("_", 1)[0]
    return lowered_map.get(base.lower())


def _select_locale():
    supported_keys = current_app.config["LANGUAGES"].keys()
    forced = current_app.config.get("FORCE_LANGUAGE") or os.getenv("FORCE_LANGUAGE")
    if forced:
        normalised = _normalize_locale(forced)
        if normalised:
            return normalised
        current_app.logger.warning(
            "FORCE_LANGUAGE=%s ignored - unsupported locale", forced
        )

    if arg := request.args.get("lang"):
        normalised = _normalize_locale(arg)
        if normalised:
            session["lang"] = normalised
            return normalised

    if stored := session.get("lang"):
        if normalised := _normalize_locale(stored):
            if normalised != stored:
                session["lang"] = normalised
            return normalised
        session.pop("lang", None)

    if best := request.accept_languages.best_match(supported_keys):
        return best

    return current_app.config.get("BABEL_DEFAULT_LOCALE", "en")


def _configure_sqlite_for_concurrency(app):
    """Configure SQLite for optimal concurrent write performance.

    Enables WAL (Write-Ahead Logging) mode which allows:
    - Multiple readers can access the database simultaneously
    - Writers don't block readers
    - One writer can proceed while readers are active
    - Much better performance for concurrent workloads (4 workers + background threads)

    SAFETY: WAL mode requires local filesystem access. It will automatically
    fall back to DELETE journal mode if the filesystem doesn't support it.

    NOTE: WAL mode is automatically disabled during testing since tests run
    sequentially and don't benefit from concurrent access.
    """
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        """Set SQLite pragmas on each new connection."""
        # Only apply to SQLite databases - check the connection itself
        try:
            cursor = dbapi_conn.cursor()
            # Quick check if this is SQLite
            cursor.execute("SELECT sqlite_version()")
            cursor.fetchone()  # If this works, it's SQLite
        except Exception:
            # Not SQLite, skip configuration
            return

        # Skip WAL mode in testing - tests are sequential and don't need concurrency
        is_testing = app.config.get("TESTING", False)

        if is_testing:
            # Use DELETE mode for tests - simpler and no WAL file issues
            cursor.execute("PRAGMA journal_mode=DELETE")
            cursor.execute("PRAGMA synchronous=FULL")
            app.logger.info(
                "🧪 SQLite testing mode: DELETE journal, FK constraints enabled"
            )
        else:
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
                cursor.execute("PRAGMA synchronous=FULL")
            else:
                app.logger.info("✅ SQLite WAL mode enabled for concurrent writes")
                cursor.execute("PRAGMA synchronous=NORMAL")
                # Auto-checkpoint only applies to WAL mode
                cursor.execute("PRAGMA wal_autocheckpoint=1000")

        # Set busy timeout to 30 seconds (works with all journal modes)
        cursor.execute("PRAGMA busy_timeout=30000")
        # Enable foreign key constraints (CRITICAL - always enabled)
        cursor.execute("PRAGMA foreign_keys=ON")
        # Larger cache size for better performance (10MB)
        cursor.execute("PRAGMA cache_size=-10000")
        cursor.close()
