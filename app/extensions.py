import os
from datetime import UTC, datetime, timedelta

from flask import current_app, request, session
from flask_apscheduler import APScheduler
from flask_babel import Babel
from flask_compress import Compress
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
compress = Compress()
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

    # The scheduler starts only in the background leader process.
    # See app/background.py and init_scheduler() below.

    htmx.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # type: ignore

    from .services import cloudflare_access

    cloudflare_access.init_app(app)
    db.init_app(app)

    # Enable SQLite WAL mode for concurrent writes
    _configure_sqlite_for_concurrency(app)

    migrate.init_app(app, db)
    limiter.init_app(app)

    # COMPRESS_REGISTER is False: app/static_assets.py compresses only the
    # static file responses. See the BREACH note in app/config.py.
    from .static_assets import compress_cache_backend, compress_cache_key

    app.config.setdefault("COMPRESS_CACHE_BACKEND", compress_cache_backend)
    app.config.setdefault("COMPRESS_CACHE_KEY", compress_cache_key)
    compress.init_app(app)
    # Flask-RESTX API will be initialized with the blueprint


# Options for each job that this module registers. A job never runs two
# times at the same time, and missed runs collapse into one run.
JOB_OPTIONS = {"replace_existing": True, "max_instances": 1, "coalesce": True}


def scheduler_disabled_by_env() -> bool:
    """Return True when WIZARR_DISABLE_SCHEDULER turns the scheduler off."""
    return os.getenv("WIZARR_DISABLE_SCHEDULER", "false").lower() in (
        "true",
        "1",
        "yes",
    )


def init_scheduler(app) -> bool:
    """Register the scheduled jobs and start the scheduler.

    Only the background leader calls this function (see app/background.py).
    Returns True when the scheduler runs.
    """
    if scheduler_disabled_by_env():
        app.logger.info("APScheduler disabled by WIZARR_DISABLE_SCHEDULER")
        return False

    # Disable the scheduler REST API for security.
    app.config["SCHEDULER_API_ENABLED"] = False
    scheduler.init_app(app)
    register_scheduled_jobs(app, scheduler)

    try:
        if not scheduler.running:
            scheduler.start()
    except Exception as e:
        app.logger.warning(f"Failed to start APScheduler: {e}")
        return False

    if scheduler.running:
        app.logger.info("APScheduler started successfully (pid %s)", os.getpid())
        return True

    # Flask-APScheduler does not start in Flask debug mode without the reloader.
    app.logger.info("APScheduler initialized but not started")
    return False


def register_scheduled_jobs(app, target_scheduler, now: datetime | None = None):
    """Add the maintenance jobs to *target_scheduler*.

    The jobs keep a reference to *app*, so the job store must stay in memory.
    """
    from app.tasks.ldap_sync import _get_ldap_sync_interval, sync_ldap_users
    from app.tasks.maintenance import (
        _get_expiry_check_interval,
        check_expiring,
        optimize_sqlite_database,
        send_expiry_reminders,
    )
    from app.tasks.update_check import fetch_and_cache_manifest

    now = now or datetime.now(UTC)

    # Process expired users soon after a restart, then at the normal interval.
    target_scheduler.add_job(
        id="check_expiring",
        func=check_expiring,
        args=[app],
        trigger="interval",
        minutes=_get_expiry_check_interval(),
        next_run_time=now + timedelta(minutes=1),
        **JOB_OPTIONS,
    )

    # Fetch the manifest soon after startup (in the background), then daily.
    target_scheduler.add_job(
        id="fetch_manifest",
        func=fetch_and_cache_manifest,
        args=[app],
        trigger="interval",
        hours=24,
        next_run_time=now + timedelta(seconds=15),
        **JOB_OPTIONS,
    )

    # Always register the LDAP sync. The job returns early when LDAP is not
    # enabled, so LDAP that you enable at runtime syncs without a restart.
    target_scheduler.add_job(
        id="sync_ldap_users",
        func=sync_ldap_users,
        args=[app],
        trigger="interval",
        minutes=_get_ldap_sync_interval(),
        next_run_time=now + timedelta(minutes=2),
        **JOB_OPTIONS,
    )

    # Always register the expiry reminder job. The job returns early when
    # SMTP/reminders are not enabled, so turning them on at runtime takes
    # effect without a restart.
    target_scheduler.add_job(
        id="send_expiry_reminders",
        func=send_expiry_reminders,
        args=[app],
        trigger="interval",
        hours=1,
        next_run_time=now + timedelta(minutes=3),
        **JOB_OPTIONS,
    )

    # Refresh the SQLite query planner statistics once a day. The startup
    # run is in app/background.py.
    target_scheduler.add_job(
        id="sqlite_optimize",
        func=optimize_sqlite_database,
        args=[app],
        trigger="interval",
        hours=24,
        **JOB_OPTIONS,
    )

    # Note: WAL auto-checkpoints every 1000 pages (~4MB) automatically.
    # Manual checkpoint jobs can be added here if needed for large .db-wal files.


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
    from .services import cloudflare_access

    # Behind Cloudflare Access the session only counts alongside a valid token,
    # so a request that skipped Access can't use an admin's session cookie.
    if cloudflare_access.enabled() and cloudflare_access.verified_claims() is None:
        return None

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
