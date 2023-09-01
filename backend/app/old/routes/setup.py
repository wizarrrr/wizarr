from os import listdir, path

from flask import Blueprint, abort, render_template
from jinja2 import TemplateNotFound

from app.security import server_not_verified_required
from helpers import get_settings

setup = Blueprint("setup", __name__, template_folder="../views/setup/")

@setup.route("/setup", defaults={"subpath": "welcome"})
@setup.route("/setup/", defaults={"subpath": "welcome"})
@setup.route("/setup/<string:subpath>")
@server_not_verified_required()
def setup_route(subpath):
    # Get all settings
    settings = get_settings()

    html_files = [path.splitext(file)[0] for file in listdir("./app/views/setup/pages") if file.endswith(".html")]

    if subpath not in html_files:
        return abort(404)

    # I could of used html_files list however I wanted to keep the order of the pages instead of alphabetical order
    pages = [
        "welcome",
        "database",
        "restore",
        "accounts",
        "settings",
        "complete"
    ]

    data = {
        "partials": [f"setup/pages/{page}.html" for page in pages],
        "current": (pages.index(subpath)) + 1,
        "pages": pages
    }

    data.update(settings)

    return render_template("setup/base.html", **data)
