from os import getenv, listdir, path

from flask import Blueprint, abort, render_template
from flask_jwt_extended import current_user
from jinja2 import TemplateNotFound
from app.utils.config_loader import load_config

from app.security import login_required
from helpers import get_api_keys, get_settings

settings = Blueprint("settings", __name__)

@settings.get("/admin/settings", defaults={"subpath": "main"})
@settings.get("/admin/settings/<path:subpath>")
@login_required()
def settings_routes(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir(
        "./app/views/settings") if file.endswith(".html")]

    # Check if the subpath is valid
    if subpath not in html_files:
        return abort(404)

    # Get all settings
    context = get_settings()
    context["api_keys"] = get_api_keys()
    context["auth"] = not bool(getenv("DISABLE_BUILTIN_AUTH"))
    context["admin"] = current_user

    # Load the settings sections
    sections = load_config("settings.json.j2")

    # All possible admin routes
    return render_template("admin.html", subpath="admin/settings.html", settings_subpath=f"settings/{subpath}.html", **context, sections=sections)
