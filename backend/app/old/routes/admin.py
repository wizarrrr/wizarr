from os import getenv, listdir, path

from flask import Blueprint, abort, render_template
from jinja2 import TemplateNotFound

from app.security import login_required
from helpers import get_settings

admin = Blueprint("admin", __name__, template_folder="../views/admin/")

@admin.get("/admin", defaults={"subpath": "invite"})
@admin.get("/admin/<path:subpath>")
@login_required()
def admin_routes(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir(
        "./app/views/admin") if file.endswith(".html")]

    # Check if the subpath is valid
    if subpath not in html_files:
        return abort(404)

    # Authentication Activated
    context = get_settings()
    context["auth"] = not bool(getenv("DISABLE_BUILTIN_AUTH"))

    # All possible admin routes
    return render_template("admin.html", subpath=f"/admin/{subpath}.html", **context)


@admin.get("/partials/admin", defaults={"subpath": ""})
@admin.get("/partials/admin/<path:subpath>")
@login_required()
def admin_partials(subpath):
    # Get valid settings partials
    html_files = [path.splitext(file)[0] for file in listdir(
        "./app/views/admin") if file.endswith(".html")]

    # Check if the subpath is valid
    if subpath not in html_files and subpath != "":
        return abort(404)

    # Get all settings
    context = get_settings()
    context["auth"] = not bool(getenv("DISABLE_BUILTIN_AUTH"))

    if not subpath:
        return render_template("main.html", **context)

    # All possible admin partials
    return render_template(f"/admin/{subpath}.html", **context)
