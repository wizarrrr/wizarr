from flask import Blueprint, send_from_directory
from jinja2 import TemplateNotFound

from os import path

main = Blueprint("main", __name__)

@main.get("/favicon.ico")
def favicon():
    # Get the static directory based on the root path of the app
    root_path = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))
    static_dir = path.join(root_path, "static")
    return send_from_directory(static_dir, "favicon.ico", mimetype="image/vnd.microsoft.icon")
