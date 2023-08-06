from flask import Blueprint, send_from_directory
from jinja2 import TemplateNotFound

from os import path
from app import app

main = Blueprint("main", __name__)

@main.get("/favicon.ico")
def favicon():
    # Get the static directory
    static_dir = path.join(app.root_path, "static")
    return send_from_directory(static_dir, "favicon.ico", mimetype="image/vnd.microsoft.icon")
