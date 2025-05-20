import os
from functools import wraps
from flask import session, redirect, current_app
from app.models import Settings
from flask_login import login_manager
from app.models import User
def builtin_login_required(view):
    """Rough clone of your old decorator; keep if Flask-Login isn’t in play."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if os.getenv("DISABLE_BUILTIN_AUTH", "").lower() == "true":
            return view(*args, **kwargs)

        if not Settings.get_or_none(Settings.key == "admin_username"):
            return redirect("/setup/")    # first-run wizard

        if session.get("admin_key") == Settings.get(Settings.key == "admin_key").value:
            return view(*args, **kwargs)

        return redirect("/login")
    return wrapped
