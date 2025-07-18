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


class NoOpLimiter:
    """A no-op limiter for development mode that disables all rate limiting."""
    
    def limit(self, *args, **kwargs):
        """Return a decorator that does nothing."""
        def decorator(func):
            return func
        return decorator
    
    def init_app(self, app):
        """No-op initialization."""
        pass


# Instantiate extensions
db = SQLAlchemy()
babel = Babel()
sess = Session()
scheduler = APScheduler()
htmx = HTMX()
login_manager = LoginManager()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address, default_limits=["200 per day", "50 per hour"]
)


# Initialize with app
def init_extensions(app):
    global limiter
    
    sess.init_app(app)
    babel.init_app(app, locale_selector=_select_locale)
    # scheduler.init_app(app)
    # scheduler.start()
    htmx.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"  # type: ignore[assignment]
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Disable rate limiting in debug/development mode
    if app.debug:
        print("Rate limiting disabled in debug mode")
        limiter = NoOpLimiter()
    
    limiter.init_app(app)
    init_security_headers(app)


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


def init_security_headers(app):
    """Initialize security headers for the application."""

    @app.after_request
    def security_headers(response):
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Prevent framing (clickjacking protection)
        response.headers["X-Frame-Options"] = "DENY"

        # Enable HSTS if running on HTTPS
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response
