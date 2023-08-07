from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound

from app.security import server_verified_required

home = Blueprint("home", __name__, template_folder="../views/home/")

@home.route("/")
@server_verified_required()
def homepage_route():
    return render_template("homepage.html")
