import os

from app.extensions import db
from app.models import Settings
from app.settings_cache import get_cached_setting


def _load_server_name() -> str | None:
    # Use no_autoflush to prevent triggering pending session changes
    with db.session.no_autoflush:
        setting = Settings.query.filter_by(key="server_name").first()
        return setting.value if setting else "Wizarr"


def inject_server_name():
    from sqlalchemy.exc import OperationalError, PendingRollbackError

    try:
        # Each render needs the name. A short cache saves one query per request.
        server_name = get_cached_setting("server_name", _load_server_name)
    except (OperationalError, PendingRollbackError) as e:
        if "database is locked" in str(e).lower():
            # Fallback to default if database is locked
            server_name = "Wizarr"
        else:
            raise

    return {"server_name": server_name}


def inject_plus_features():
    """Inject Plus features availability into template context."""
    try:
        import plus

        is_plus_enabled = plus.is_plus_enabled()  # type: ignore
    except (ImportError, AttributeError):
        is_plus_enabled = False

    return {"is_plus_enabled": is_plus_enabled}


def inject_app_version():
    """Inject current app version into template context for cache busting."""
    return {"app_version": os.getenv("APP_VERSION", "dev")}
