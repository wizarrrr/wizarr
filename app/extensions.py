from flask import current_app, request, session
from flask_apscheduler import APScheduler
from flask_babel import Babel
from flask_htmx import HTMX
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_restx import Api
from flask_sqlalchemy import SQLAlchemy

from flask_session import Session

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
        from app.tasks.maintenance import _get_expiry_check_interval, check_expiring

        # Add the task to the scheduler, passing the app instance
        scheduler.add_job(
            id="check_expiring",
            func=lambda: check_expiring(app),
            trigger="interval",
            minutes=_get_expiry_check_interval(),
            replace_existing=True,
        )

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
    migrate.init_app(app, db)
    limiter.init_app(app)
    # Flask-RESTX API will be initialized with the blueprint


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
