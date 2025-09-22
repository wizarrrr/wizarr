from app.extensions import db
from app.models import Settings


def inject_server_name():
    from sqlalchemy.exc import OperationalError, PendingRollbackError

    try:
        # Use no_autoflush to prevent triggering pending session changes
        with db.session.no_autoflush:
            setting = Settings.query.filter_by(key="server_name").first()
            server_name = setting.value if setting else "Wizarr"
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

        is_plus_enabled = plus.is_plus_enabled()
    except ImportError:
        is_plus_enabled = False

    return {"is_plus_enabled": is_plus_enabled}
