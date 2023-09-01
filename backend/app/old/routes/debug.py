from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound

from app.security import server_verified_required

debug = Blueprint("debug", __name__, template_folder="../views/client/")

@debug.route("/debug")
@server_verified_required()
def homepage_route():
    return render_template("admin.html", subpath="debug.html")
