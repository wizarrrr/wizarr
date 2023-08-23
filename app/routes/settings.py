from os import getenv, listdir, path

from flask import Blueprint, abort, render_template
from flask_jwt_extended import current_user
from jinja2 import TemplateNotFound
from app.utils.config_loader import load_config

from app.security import login_required
from helpers import get_api_keys, get_settings

settings = Blueprint("settings", __name__, template_folder="../views/settings/")

@settings.get("/admin/settings", defaults={"subpath": ""})
@settings.get("/admin/settings/<path:subpath>")
@login_required()
def settings_routes(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir(
        "./app/views/settings") if file.endswith(".html")]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    context = get_settings()
    context["api_keys"] = get_api_keys()
    context["auth"] = not bool(getenv("DISABLE_BUILTIN_AUTH"))
    context["admin"] = current_user

    # Load the settings sections
    sections = load_config("settings.json.j2")

    if not subpath:
        return render_template("admin.html", subpath="/admin/settings.html", settings_subpath="/settings/main.html", **context, sections=sections)

    # All possible admin routes
    return render_template("admin.html", subpath="/admin/settings.html", settings_subpath=f"/settings/{subpath}.html", **context, sections=sections)


@settings.get("/partials/admin/settings", defaults={"subpath": ""})
@settings.get("/partials/admin/settings/<path:subpath>")
@login_required()
def settings_partials(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir(
        "./app/views/settings") if file.endswith(".html")]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    context = get_settings()
    context["api_keys"] = get_api_keys()
    context["auth"] = not bool(getenv("DISABLE_BUILTIN_AUTH"))
    context["admin"] = current_user

    # Load the settings sections
    sections = load_config("settings.json.j2")

    if not subpath:
        return render_template("/admin/settings.html", settings_subpath="/settings/main.html", **context, sections=sections)

    # All possible admin partials
    return render_template(f"/settings/{subpath}.html", **context, sections=sections)
