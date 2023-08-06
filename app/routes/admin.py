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
    settings = get_settings()
    settings["auth"] = not bool(getenv("DISABLE_BUILTIN_AUTH"))

    # All possible admin routes
    return render_template("admin.html", subpath=f"{subpath}.html", **settings)
