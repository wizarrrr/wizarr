# app/middleware.py
from flask import current_app, redirect, request, url_for

from app.models import Settings
from app.settings_cache import get_cached_setting


def _load_admin_username() -> str | None:
    admin_setting = Settings.query.filter_by(key="admin_username").first()
    return admin_setting.value if admin_setting else None


def require_onboarding():
    if (
        request.path.startswith("/setup")
        or request.path.startswith("/static")
        or request.path.startswith("/settings")
        or request.path.startswith("/api")
    ):
        return None

    # Skip onboarding check during testing
    if current_app.config.get("TESTING"):
        return None

    # Check if an admin user exists. The cache keeps only a found admin, so
    # the check sees at once when onboarding finishes.
    admin_username = get_cached_setting(
        "admin_username", _load_admin_username, cache_empty=False
    )
    if not admin_username:
        return redirect(url_for("setup.onboarding"))
    return None
    # Allow access to the application even if no MediaServer has been configured yet.
    # Users can add servers later via the Settings page.
