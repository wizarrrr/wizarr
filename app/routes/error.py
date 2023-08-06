from logging import getLogger

from flask import Blueprint, abort, render_template
from jinja2 import TemplateNotFound

from app import app

logger = getLogger(__name__)

@app.errorhandler(404)
def page_not_found(e):
    logger.error("Page not found: %s", e)
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error("Internal server error: %s", e)
    return render_template("errors/500.html"), 500

@app.errorhandler(401)
def unauthorized(e):
    logger.error("Unauthorized: %s", e)
    return render_template("errors/401.html"), 401
